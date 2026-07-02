from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from math import isfinite
from typing import Any, ClassVar


@dataclass(slots=True)
class Aeroplane:
    """Самолёт, полученный из API OpenSky."""

    ICAO24_PATTERN: ClassVar[re.Pattern[str]] = re.compile(r"^[0-9a-f]{6}$")

    icao24: str
    callsign: str | None
    origin_country: str
    velocity: float | None
    altitude: float | None
    longitude: float | None = None
    latitude: float | None = None
    on_ground: bool = False
    heading: float | None = None
    vertical_rate: float | None = None
    last_contact: int | None = None

    def __post_init__(self) -> None:
        self.icao24 = self._validate_icao24(self.icao24)
        self.callsign = self._validate_callsign(self.callsign)
        self.origin_country = self._validate_country(self.origin_country)

        self.velocity = self._validate_optional_number(
            self.velocity,
            "Скорость",
            minimum=0,
        )
        self.altitude = self._validate_optional_number(
            self.altitude,
            "Высота",
            minimum=-1000,
        )
        self.longitude = self._validate_optional_number(
            self.longitude,
            "Долгота",
            minimum=-180,
            maximum=180,
        )
        self.latitude = self._validate_optional_number(
            self.latitude,
            "Широта",
            minimum=-90,
            maximum=90,
        )
        self.heading = self._validate_optional_number(
            self.heading,
            "Направление",
            minimum=0,
            maximum=360,
        )
        self.vertical_rate = self._validate_optional_number(
            self.vertical_rate,
            "Вертикальная скорость",
        )

        if not isinstance(self.on_ground, bool):
            raise TypeError("on_ground должен иметь тип bool.")

        if self.last_contact is not None:
            if (
                isinstance(self.last_contact, bool)
                or not isinstance(self.last_contact, int)
                or self.last_contact < 0
            ):
                raise ValueError(
                    "last_contact должен быть неотрицательным целым числом."
                )

    @staticmethod
    def _validate_icao24(value: str) -> str:
        if not isinstance(value, str):
            raise TypeError("icao24 должен иметь тип str.")

        normalized_value = value.strip().lower()

        if not Aeroplane.ICAO24_PATTERN.fullmatch(normalized_value):
            raise ValueError(
                "icao24 должен состоять из шести "
                "шестнадцатеричных символов."
            )

        return normalized_value

    @staticmethod
    def _validate_callsign(value: str | None) -> str | None:
        if value is None:
            return None

        if not isinstance(value, str):
            raise TypeError("Позывной должен иметь тип str или None.")

        normalized_value = value.strip().upper()

        if not normalized_value:
            return None

        if len(normalized_value) > 8:
            raise ValueError("Позывной не может быть длиннее 8 символов.")

        return normalized_value

    @staticmethod
    def _validate_country(value: str) -> str:
        if not isinstance(value, str):
            raise TypeError("Страна регистрации должна иметь тип str.")

        normalized_value = value.strip()

        if not normalized_value:
            raise ValueError("Страна регистрации не может быть пустой.")

        return normalized_value

    @staticmethod
    def _validate_optional_number(
        value: float | int | None,
        field_name: str,
        minimum: float | None = None,
        maximum: float | None = None,
    ) -> float | None:
        if value is None:
            return None

        if isinstance(value, bool):
            raise TypeError(f"{field_name} должно быть числом или None.")

        try:
            normalized_value = float(value)
        except (TypeError, ValueError) as error:
            raise TypeError(
                f"{field_name} должно быть числом или None."
            ) from error

        if not isfinite(normalized_value):
            raise ValueError(
                f"{field_name} должно быть конечным числом."
            )

        if minimum is not None and normalized_value < minimum:
            raise ValueError(
                f"{field_name} не может быть меньше {minimum}."
            )

        if maximum is not None and normalized_value > maximum:
            raise ValueError(
                f"{field_name} не может быть больше {maximum}."
            )

        return normalized_value

    @property
    def altitude_for_comparison(self) -> float:
        """Возвращает высоту, считая отсутствие данных минимумом."""
        return self.altitude if self.altitude is not None else float("-inf")

    @property
    def velocity_for_comparison(self) -> float:
        """Возвращает скорость, считая отсутствие данных минимумом."""
        return self.velocity if self.velocity is not None else float("-inf")

    def __lt__(self, other: object) -> bool:
        if not isinstance(other, Aeroplane):
            return NotImplemented

        return self.altitude_for_comparison < other.altitude_for_comparison

    def __gt__(self, other: object) -> bool:
        if not isinstance(other, Aeroplane):
            return NotImplemented

        return self.altitude_for_comparison > other.altitude_for_comparison

    def is_faster_than(self, other: Aeroplane) -> bool:
        """Проверяет, летит ли текущий самолёт быстрее другого."""
        self._validate_other_aeroplane(other)
        return self.velocity_for_comparison > other.velocity_for_comparison

    def compare_speed(self, other: Aeroplane) -> int:
        """Сравнение самолётов по скорости"""
        self._validate_other_aeroplane(other)

        if self.velocity_for_comparison > other.velocity_for_comparison:
            return 1

        if self.velocity_for_comparison < other.velocity_for_comparison:
            return -1

        return 0

    def compare_altitude(self, other: Aeroplane) -> int:
        """Сравнение самолётов по высоте."""
        self._validate_other_aeroplane(other)

        if self.altitude_for_comparison > other.altitude_for_comparison:
            return 1

        if self.altitude_for_comparison < other.altitude_for_comparison:
            return -1

        return 0

    @staticmethod
    def _validate_other_aeroplane(other: Aeroplane) -> None:
        if not isinstance(other, Aeroplane):
            raise TypeError("Сравнение возможно только с объектом Aeroplane.")

    @classmethod
    def from_state_vector(cls, state: list[Any]) -> Aeroplane:
        """Создаёт Aeroplane из state vector, возвращаемого OpenSky API."""
        if len(state) < 12:
            raise ValueError(
                "State vector OpenSky должен содержать минимум 12 значений."
            )

        altitude = state[7]

        if altitude is None and len(state) > 13:
            altitude = state[13]

        return cls(
            icao24=state[0],
            callsign=state[1],
            origin_country=state[2] or "Неизвестно",
            last_contact=state[4],
            longitude=state[5],
            latitude=state[6],
            altitude=altitude,
            on_ground=bool(state[8]),
            velocity=state[9],
            heading=state[10],
            vertical_rate=state[11],
        )

    @classmethod
    def cast_to_object_list(
        cls,
        states: list[list[Any]] | None,
    ) -> list[Aeroplane]:
        """Преобразует данные OpenSky в список объектов Aeroplane."""
        if not states:
            return []

        aeroplanes: list[Aeroplane] = []

        for state in states:
            try:
                aeroplanes.append(cls.from_state_vector(state))
            except (TypeError, ValueError):
                continue

        return aeroplanes

    def to_dict(self) -> dict[str, Any]:
        """Подготавливает данные самолёта для сохранения в JSON."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Aeroplane:
        """Создаёт объект Aeroplane из словаря JSON."""
        return cls(**data)

    def __str__(self) -> str:
        callsign = self.callsign or "Без позывного"

        altitude = (
            f"{self.altitude:.0f} м"
            if self.altitude is not None
            else "нет данных"
        )

        velocity = (
            f"{self.velocity:.1f} м/с"
            if self.velocity is not None
            else "нет данных"
        )

        status = "на земле" if self.on_ground else "в воздухе"

        return (
            f"{callsign} | ICAO24: {self.icao24} | "
            f"Страна: {self.origin_country} | "
            f"Высота: {altitude} | "
            f"Скорость: {velocity} | "
            f"Статус: {status}"
        )
