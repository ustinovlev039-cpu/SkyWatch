from __future__ import annotations

import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent
SRC_DIRECTORY = PROJECT_ROOT / "src"

if str(SRC_DIRECTORY) not in sys.path:
    sys.path.insert(0, str(SRC_DIRECTORY))


from skywatch.api import AeroplanesAPI, SkyWatchAPIError  # noqa: E402
from skywatch.models import Aeroplane  # noqa: E402
from skywatch.services import AeroplaneService  # noqa: E402
from skywatch.storage import JSONSaver, StorageError  # noqa: E402


DATA_FILE = PROJECT_ROOT / "data" / "aeroplanes.json"


def print_menu() -> None:
    """Выводит главное меню SkyWatch."""
    print(
        """
SkyWatch

1. Получить самолёты над страной
2. Показать текущий список самолётов
3. Получить топ N самолётов по высоте
4. Найти самолёты по стране регистрации
5. Сохранить текущий список в JSON
6. Показать сохранённые самолёты
7. Удалить самолёт из JSON по ICAO24
0. Выйти
"""
    )


def print_aeroplanes(aeroplanes: list[Aeroplane]) -> None:
    """Выводит список самолётов в консоль."""
    if not aeroplanes:
        print("\nСамолёты не найдены.\n")
        return

    print(f"\nНайдено самолётов: {len(aeroplanes)}\n")

    for number, aeroplane in enumerate(aeroplanes, start=1):
        print(f"{number}. {aeroplane}")

    print()


def read_positive_integer(prompt: str) -> int:
    """Запрашивает у пользователя положительное целое число."""
    while True:
        raw_value = input(prompt).strip()

        try:
            value = int(raw_value)
        except ValueError:
            print("Введите целое число.")
            continue

        if value <= 0:
            print("Число должно быть больше нуля.")
            continue

        return value


def has_current_request(current_country: str | None) -> bool:
    """Проверяет, был ли выполнен запрос к API."""
    if current_country is not None:
        return True

    print(
        "\nСначала получите данные о самолётах через пункт 1.\n"
    )
    return False


def request_aeroplanes(
    api: AeroplanesAPI,
) -> tuple[str | None, list[Aeroplane]]:
    """Получает список самолётов над введённой пользователем страной."""
    country = input("\nВведите название страны на английском: ").strip()

    if not country:
        print("Название страны не может быть пустым.\n")
        return None, []

    try:
        aeroplanes = api.get_aeroplanes(country)
    except (SkyWatchAPIError, TypeError, ValueError) as error:
        print(f"\nНе удалось получить данные: {error}\n")
        return None, []

    print(f"\nРезультат запроса для страны: {country}")
    print_aeroplanes(aeroplanes)

    return country, aeroplanes


def show_top_by_altitude(
    current_country: str | None,
    aeroplanes: list[Aeroplane],
) -> None:
    """Показывает топ N самолётов по высоте."""
    if not has_current_request(current_country):
        return

    limit = read_positive_integer(
        "Введите количество самолётов для топа: "
    )

    top_aeroplanes = AeroplaneService.get_top_by_altitude(aeroplanes, limit)

    print("\nТоп самолётов по высоте:")
    print_aeroplanes(top_aeroplanes)


def filter_by_registration_country(
    current_country: str | None,
    aeroplanes: list[Aeroplane],
) -> None:
    """Ищет самолёты по стране регистрации."""
    if not has_current_request(current_country):
        return

    country = input("Введите страну регистрации самолёта: ").strip()

    try:
        filtered_aeroplanes = AeroplaneService.filter_by_origin_country(
            aeroplanes,
            country,
        )
    except ValueError as error:
        print(f"\nОшибка: {error}\n")
        return

    print(f"\nСамолёты страны регистрации «{country}»:")
    print_aeroplanes(filtered_aeroplanes)


def save_current_aeroplanes(
    current_country: str | None,
    aeroplanes: list[Aeroplane],
    storage: JSONSaver,
) -> None:
    """Сохраняет текущий результат запроса в JSON."""
    if not has_current_request(current_country):
        return

    try:
        for aeroplane in aeroplanes:
            storage.add_aeroplane(aeroplane)
    except StorageError as error:
        print(f"\nНе удалось сохранить данные: {error}\n")
        return

    print(
        f"\nВ JSON сохранено или обновлено самолётов: "
        f"{len(aeroplanes)}.\n"
    )


def show_saved_aeroplanes(storage: JSONSaver) -> None:
    """Показывает самолёты, сохранённые в JSON-файле."""
    try:
        aeroplanes = storage.get_all_aeroplanes()
    except StorageError as error:
        print(f"\nНе удалось прочитать JSON-файл: {error}\n")
        return

    print("\nСамолёты из JSON-хранилища:")
    print_aeroplanes(aeroplanes)


def delete_aeroplane_from_storage(storage: JSONSaver) -> None:
    """Удаляет самолёт из JSON-файла по ICAO24."""
    icao24 = input(
        "Введите ICAO24 самолёта для удаления: "
    ).strip()

    if not icao24:
        print("ICAO24 не может быть пустым.\n")
        return

    try:
        was_deleted = storage.delete_aeroplane_by_icao24(icao24)
    except StorageError as error:
        print(f"\nНе удалось удалить самолёт: {error}\n")
        return

    if was_deleted:
        print(f"\nСамолёт с ICAO24 {icao24.lower()} удалён.\n")
    else:
        print(f"\nСамолёт с ICAO24 {icao24.lower()} не найден.\n")


def main() -> None:
    """Запускает консольное приложение SkyWatch."""
    api = AeroplanesAPI()
    storage = JSONSaver(DATA_FILE)

    current_country: str | None = None
    current_aeroplanes: list[Aeroplane] = []

    print("Добро пожаловать в SkyWatch!")

    while True:
        print_menu()
        choice = input("Выберите действие: ").strip()

        if choice == "0":
            print("\nРабота SkyWatch завершена.")
            break

        if choice == "1":
            country, aeroplanes = request_aeroplanes(api)

            if country is not None:
                current_country = country
                current_aeroplanes = aeroplanes

            continue

        if choice == "2":
            if has_current_request(current_country):
                print_aeroplanes(current_aeroplanes)
            continue

        if choice == "3":
            show_top_by_altitude(
                current_country,
                current_aeroplanes,
            )
            continue

        if choice == "4":
            filter_by_registration_country(
                current_country,
                current_aeroplanes,
            )
            continue

        if choice == "5":
            save_current_aeroplanes(
                current_country,
                current_aeroplanes,
                storage,
            )
            continue

        if choice == "6":
            show_saved_aeroplanes(storage)
            continue

        if choice == "7":
            delete_aeroplane_from_storage(storage)
            continue

        print("\nНеизвестная команда. Выберите пункт из меню.\n")


if __name__ == "__main__":
    main()
