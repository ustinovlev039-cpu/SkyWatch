from __future__ import annotations

from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass
from math import isfinite

from skywatch.models import Aeroplane


@dataclass(frozen=True, slots=True)
class AeroplaneStatistics:
    """Сводная статистика по набору самолётов."""

    total_count: int
    airborne_count: int
    grounded_count: int
    average_altitude: float | None
    average_velocity: float | None
    highest_aeroplane: Aeroplane | None
    fastest_aeroplane: Aeroplane | None
    countries_count: dict[str, int]


class AeroplaneService:
    """Сервис для фильтрации, сортировки и анализа самолётов"""

    @staticmethod
    def sort_by_altitude(
        aeroplanes: Iterable[Aeroplane],
        descending: bool = True,
    ) -> list[Aeroplane]:
        """Сортирует самолёты по высоте полёта."""
        AeroplaneService._validate_descending(descending)
        validated_aeroplanes = AeroplaneService._validate_aeroplanes(
            aeroplanes
        )

        return sorted(
            validated_aeroplanes,
            key=lambda aeroplane: aeroplane.altitude_for_comparison,
            reverse=descending,
        )

    @staticmethod
    def sort_by_velocity(
        aeroplanes: Iterable[Aeroplane],
        descending: bool = True,
    ) -> list[Aeroplane]:
        """Сортирует самолёты по скорости."""
        AeroplaneService._validate_descending(descending)
        validated_aeroplanes = AeroplaneService._validate_aeroplanes(
            aeroplanes
        )

        return sorted(
            validated_aeroplanes,
            key=lambda aeroplane: aeroplane.velocity_for_comparison,
            reverse=descending,
        )

    @staticmethod
    def get_top_by_altitude(
        aeroplanes: Iterable[Aeroplane],
        limit: int,
    ) -> list[Aeroplane]:
        """Возвращает топ N самолётов по высоте."""
        AeroplaneService._validate_limit(limit)

        sorted_aeroplanes = AeroplaneService.sort_by_altitude(aeroplanes)

        return sorted_aeroplanes[:limit]

    @staticmethod
    def get_top_by_velocity(
        aeroplanes: Iterable[Aeroplane],
        limit: int,
    ) -> list[Aeroplane]:
        """Возвращает топ N самолётов по скорости."""
        AeroplaneService._validate_limit(limit)

        sorted_aeroplanes = AeroplaneService.sort_by_velocity(aeroplanes)

        return sorted_aeroplanes[:limit]

    @staticmethod
    def filter_by_origin_country(
        aeroplanes: Iterable[Aeroplane],
        country: str,
    ) -> list[Aeroplane]:
        """Фильтрует самолёты по стране регистрации."""
        if not isinstance(country, str):
            raise TypeError(
                "Страна регистрации для фильтрации должна быть строкой."
            )

        if not country.strip():
            raise ValueError(
                "Страна регистрации для фильтрации не может быть пустой."
            )

        normalized_country = country.strip().casefold()

        validated_aeroplanes = AeroplaneService._validate_aeroplanes(
            aeroplanes
        )

        return [
            aeroplane
            for aeroplane in validated_aeroplanes
            if aeroplane.origin_country.casefold() == normalized_country
        ]

    @staticmethod
    def filter_by_altitude_range(
        aeroplanes: Iterable[Aeroplane],
        minimum_altitude: float,
        maximum_altitude: float,
    ) -> list[Aeroplane]:
        """Возвращает самолёты в указанном диапазоне высот"""
        minimum = AeroplaneService._validate_number(
            value=minimum_altitude,
            field_name="Минимальная высота",
        )
        maximum = AeroplaneService._validate_number(
            value=maximum_altitude,
            field_name="Максимальная высота",
        )

        if minimum > maximum:
            raise ValueError(
                "Минимальная высота не может быть больше максимальной."
            )

        validated_aeroplanes = AeroplaneService._validate_aeroplanes(
            aeroplanes
        )

        return [
            aeroplane
            for aeroplane in validated_aeroplanes
            if aeroplane.altitude is not None
            and minimum <= aeroplane.altitude <= maximum
        ]

    @staticmethod
    def filter_by_ground_status(
        aeroplanes: Iterable[Aeroplane],
        on_ground: bool,
    ) -> list[Aeroplane]:
        """Фильтрует самолёты по признаку нахождения на земле."""
        if not isinstance(on_ground, bool):
            raise TypeError("on_ground должен иметь тип bool.")

        validated_aeroplanes = AeroplaneService._validate_aeroplanes(
            aeroplanes
        )

        return [
            aeroplane
            for aeroplane in validated_aeroplanes
            if aeroplane.on_ground is on_ground
        ]

    @staticmethod
    def get_statistics(aeroplanes: Iterable[Aeroplane]) -> AeroplaneStatistics:
        """Возвращает сводную статистику по переданным самолётам."""
        validated_aeroplanes = AeroplaneService._validate_aeroplanes(
            aeroplanes
        )

        airborne_aeroplanes = [
            aeroplane
            for aeroplane in validated_aeroplanes
            if not aeroplane.on_ground
        ]

        grounded_aeroplanes = [
            aeroplane
            for aeroplane in validated_aeroplanes
            if aeroplane.on_ground
        ]

        altitudes = [
            aeroplane.altitude
            for aeroplane in validated_aeroplanes
            if aeroplane.altitude is not None
        ]

        velocities = [
            aeroplane.velocity
            for aeroplane in validated_aeroplanes
            if aeroplane.velocity is not None
        ]

        aeroplanes_with_altitude = [
            aeroplane
            for aeroplane in validated_aeroplanes
            if aeroplane.altitude is not None
        ]

        aeroplanes_with_velocity = [
            aeroplane
            for aeroplane in validated_aeroplanes
            if aeroplane.velocity is not None
        ]

        countries_count = dict(
            Counter(
                aeroplane.origin_country
                for aeroplane in validated_aeroplanes
            )
        )

        return AeroplaneStatistics(
            total_count=len(validated_aeroplanes),
            airborne_count=len(airborne_aeroplanes),
            grounded_count=len(grounded_aeroplanes),
            average_altitude=(
                sum(altitudes) / len(altitudes)
                if altitudes
                else None
            ),
            average_velocity=(
                sum(velocities) / len(velocities)
                if velocities
                else None
            ),
            highest_aeroplane=(
                max(
                    aeroplanes_with_altitude,
                    key=lambda aeroplane: aeroplane.altitude_for_comparison,
                )
                if aeroplanes_with_altitude
                else None
            ),
            fastest_aeroplane=(
                max(
                    aeroplanes_with_velocity,
                    key=lambda aeroplane: aeroplane.velocity_for_comparison,
                )
                if aeroplanes_with_velocity
                else None
            ),
            countries_count=countries_count,
        )

    @staticmethod
    def _validate_aeroplanes(
        aeroplanes: Iterable[Aeroplane],
    ) -> list[Aeroplane]:
        """Проверяет набор самолётов и преобразует его в список."""
        try:
            validated_aeroplanes = list(aeroplanes)
        except TypeError as error:
            raise TypeError(
                "aeroplanes должен быть итерируемым объектом."
            ) from error

        for aeroplane in validated_aeroplanes:
            if not isinstance(aeroplane, Aeroplane):
                raise TypeError(
                    "Список должен содержать только объекты Aeroplane."
                )

        return validated_aeroplanes

    @staticmethod
    def _validate_limit(limit: int) -> None:
        """Проверяет корректность числа элементов для топа."""
        if isinstance(limit, bool) or not isinstance(limit, int):
            raise TypeError("Количество самолётов должно быть целым числом.")

        if limit <= 0:
            raise ValueError(
                "Количество самолётов для вывода должно быть больше нуля."
            )

    @staticmethod
    def _validate_number(value: float, field_name: str) -> float:
        """Проверяет и преобразует число."""
        if isinstance(value, bool):
            raise TypeError(f"{field_name} должно быть числом.")

        try:
            normalized_value = float(value)
        except (TypeError, ValueError) as error:
            raise TypeError(
                f"{field_name} должно быть числом."
            ) from error

        if not isfinite(normalized_value):
            raise ValueError(
                f"{field_name} должно быть конечным числом."
            )

        return normalized_value

    @staticmethod
    def _validate_descending(descending: bool) -> None:
        """Проверяет направление сортировки."""
        if not isinstance(descending, bool):
            raise TypeError("descending должен иметь тип bool.")
