from __future__ import annotations

import json
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from skywatch.models import Aeroplane


class StorageError(Exception):
    """Базовая ошибка при работе с хранилищем."""


class StorageDataError(StorageError):
    """Ошибка некорректных данных в файле хранилища."""


class BaseStorage(ABC):
    """Абстрактный класс для работы с хранилищем самолётов."""

    @abstractmethod
    def add_aeroplane(self, aeroplane: Aeroplane) -> None:
        """Добавляет самолёт в хранилище."""

    @abstractmethod
    def get_aeroplanes(
        self,
        **criteria: Any,
    ) -> list[Aeroplane]:
        """Возвращает самолёты по указанным критериям."""

    @abstractmethod
    def delete_aeroplane(self, aeroplane: Aeroplane) -> bool:
        """Удаляет самолёт из хранилища."""

    @abstractmethod
    def get_all_aeroplanes(self) -> list[Aeroplane]:
        """Возвращает все самолёты из хранилища."""


class JSONSaver(BaseStorage):
    """Хранилище самолётов в JSON-файле."""

    ALLOWED_CRITERIA = {
        "icao24",
        "callsign",
        "origin_country",
        "on_ground",
    }

    def __init__(self, file_path: str | Path = "data/aeroplanes.json") -> None:
        try:
            self._file_path = Path(file_path)
        except TypeError as error:
            raise TypeError(
                "Путь к JSON-файлу должен быть строкой или объектом Path."
            ) from error

        try:
            self._file_path.parent.mkdir(parents=True, exist_ok=True)
        except OSError as error:
            raise StorageError(
                f"Не удалось создать каталог {self._file_path.parent}."
            ) from error

        if not self._file_path.exists():
            self._write_data([])

    def add_aeroplane(self, aeroplane: Aeroplane) -> None:
        """Добавляет новый самолёт или обновляет существующий по ICAO24."""
        if not isinstance(aeroplane, Aeroplane):
            raise TypeError(
                "В хранилище можно добавить только объект Aeroplane."
            )

        aeroplanes = self.get_all_aeroplanes()

        for index, existing_aeroplane in enumerate(aeroplanes):
            if existing_aeroplane.icao24 == aeroplane.icao24:
                aeroplanes[index] = aeroplane
                self._write_aeroplanes(aeroplanes)
                return

        aeroplanes.append(aeroplane)
        self._write_aeroplanes(aeroplanes)

    def get_all_aeroplanes(self) -> list[Aeroplane]:
        """Загружает все сохранённые самолёты из JSON."""
        raw_data = self._read_data()

        aeroplanes: list[Aeroplane] = []

        for item in raw_data:
            if not isinstance(item, dict):
                raise StorageDataError(
                    "Каждая запись в JSON должна быть объектом."
                )

            try:
                aeroplanes.append(Aeroplane.from_dict(item))
            except (TypeError, ValueError) as error:
                raise StorageDataError(
                    "В JSON обнаружены некорректные данные самолёта."
                ) from error

        return aeroplanes

    def get_aeroplanes(
        self,
        **criteria: Any,
    ) -> list[Aeroplane]:
        """Возвращает самолёты, подходящие под критерии."""
        self._validate_criteria(criteria)

        aeroplanes = self.get_all_aeroplanes()

        return [
            aeroplane
            for aeroplane in aeroplanes
            if self._matches_criteria(aeroplane, criteria)
        ]

    def delete_aeroplane(self, aeroplane: Aeroplane) -> bool:
        """Удаляет самолёт по ICAO24."""
        if not isinstance(aeroplane, Aeroplane):
            raise TypeError(
                "Удалить можно только объект Aeroplane."
            )

        aeroplanes = self.get_all_aeroplanes()

        filtered_aeroplanes = [
            item
            for item in aeroplanes
            if item.icao24 != aeroplane.icao24
        ]

        if len(filtered_aeroplanes) == len(aeroplanes):
            return False

        self._write_aeroplanes(filtered_aeroplanes)
        return True

    def delete_aeroplane_by_icao24(self, icao24: str) -> bool:
        """Удаляет самолёт по его ICAO24-идентификатору."""
        normalized_icao24 = str(icao24).strip().lower()

        aeroplanes = self.get_all_aeroplanes()

        filtered_aeroplanes = [
            item
            for item in aeroplanes
            if item.icao24 != normalized_icao24
        ]

        if len(filtered_aeroplanes) == len(aeroplanes):
            return False

        self._write_aeroplanes(filtered_aeroplanes)
        return True

    def _read_data(self) -> list[dict[str, Any]]:
        """Читает JSON-файл и возвращает список словарей."""
        try:
            with self._file_path.open(
                "r",
                encoding="utf-8",
            ) as file:
                data = json.load(file)
        except json.JSONDecodeError as error:
            raise StorageDataError(
                "Файл JSON повреждён или содержит неверный формат данных."
            ) from error
        except OSError as error:
            raise StorageError(
                f"Не удалось прочитать файл {self._file_path}."
            ) from error

        if not isinstance(data, list):
            raise StorageDataError(
                "Корень JSON-файла должен содержать список самолётов."
            )

        return data

    def _write_aeroplanes(
        self,
        aeroplanes: list[Aeroplane],
    ) -> None:
        """Преобразует объекты Aeroplane в данные и сохраняет их."""
        data = [aeroplane.to_dict() for aeroplane in aeroplanes]

        self._write_data(data)

    def _write_data(self, data: list[dict[str, Any]]) -> None:
        """Записывает данные в JSON-файл."""
        try:
            with self._file_path.open("w", encoding="utf-8") as file:
                json.dump(data, file, ensure_ascii=False, indent=4)
        except OSError as error:
            raise StorageError(
                f"Не удалось записать данные в файл {self._file_path}."
            ) from error

    def _validate_criteria(self, criteria: dict[str, Any]) -> None:
        """Проверяет, что для поиска переданы поддерживаемые поля."""
        unknown_criteria = set(criteria) - self.ALLOWED_CRITERIA

        if unknown_criteria:
            unknown_fields = ", ".join(sorted(unknown_criteria))
            raise ValueError(
                f"Неподдерживаемые критерии поиска: {unknown_fields}."
            )

    @staticmethod
    def _matches_criteria(
        aeroplane: Aeroplane,
        criteria: dict[str, Any],
    ) -> bool:
        """Проверяет соответствие объекта всем условиям поиска."""
        for field_name, expected_value in criteria.items():
            actual_value = getattr(aeroplane, field_name)

            if isinstance(actual_value, str) and isinstance(
                expected_value,
                str,
            ):
                if (
                    actual_value.casefold()
                    != expected_value.strip().casefold()
                ):
                    return False
            elif actual_value != expected_value:
                return False

        return True
