from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from math import isfinite
from typing import Any

import requests

from skywatch.models import Aeroplane


class SkyWatchAPIError(Exception):
    """Базовая ошибка при работе с внешними API."""


class CountryNotFoundError(SkyWatchAPIError):
    """Ошибка, когда страна не найдена в Nominatim."""


class InvalidAPIResponseError(SkyWatchAPIError):
    """Ошибка, когда API вернул ответ в неожиданном формате."""


@dataclass(frozen=True, slots=True)
class BoundingBox:
    """Прямоугольная географическая область страны."""

    south_latitude: float
    north_latitude: float
    west_longitude: float
    east_longitude: float

    def __post_init__(self) -> None:
        coordinates = {
            "Южная широта": self.south_latitude,
            "Северная широта": self.north_latitude,
            "Западная долгота": self.west_longitude,
            "Восточная долгота": self.east_longitude,
        }

        for field_name, value in coordinates.items():
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise TypeError(f"{field_name} должна быть числом.")

            if not isfinite(value):
                raise ValueError(
                    f"{field_name} должна быть конечным числом."
                )

        if not -90 <= self.south_latitude <= 90:
            raise ValueError(
                "Южная широта должна быть в диапазоне от -90 до 90."
            )

        if not -90 <= self.north_latitude <= 90:
            raise ValueError(
                "Северная широта должна быть в диапазоне от -90 до 90."
            )

        if not -180 <= self.west_longitude <= 180:
            raise ValueError(
                "Западная долгота должна быть в диапазоне от -180 до 180."
            )

        if not -180 <= self.east_longitude <= 180:
            raise ValueError(
                "Восточная долгота должна быть в диапазоне от -180 до 180."
            )

        if self.south_latitude > self.north_latitude:
            raise ValueError(
                "Южная широта не может быть больше северной широты."
            )

        if self.west_longitude > self.east_longitude:
            raise ValueError(
                "Западная долгота не может быть больше восточной долготы."
            )

    def to_opensky_params(self) -> dict[str, float]:
        """Преобразует координаты в параметры запроса OpenSky."""

        return {
            "lamin": self.south_latitude,
            "lomin": self.west_longitude,
            "lamax": self.north_latitude,
            "lomax": self.east_longitude,
        }


class BaseAPIClient(ABC):
    """Абстрактный базовый класс для клиентов внешних API."""

    base_url: str

    @abstractmethod
    def fetch(self, *args: Any, **kwargs: Any) -> Any:
        """Получает данные из конкретного внешнего API."""


class _HTTPJSONClient(BaseAPIClient):
    """Общая реализация HTTP-запросов для клиентов API."""

    def __init__(
        self,
        session: requests.Session | None = None,
        timeout: int = 15,
    ) -> None:
        if isinstance(timeout, bool) or not isinstance(timeout, int):
            raise TypeError("Таймаут должен быть целым числом.")

        if timeout <= 0:
            raise ValueError("Таймаут должен быть больше нуля.")

        self._session = session or requests.Session()
        self._timeout = timeout

    def _get_json(
        self,
        endpoint: str,
        params: dict[str, Any],
        headers: dict[str, str] | None = None,
    ) -> Any:
        """Выполняет GET-запрос и возвращает JSON-ответ."""

        url = f"{self.base_url}{endpoint}"

        try:
            response = self._session.get(
                url,
                params=params,
                headers=headers,
                timeout=self._timeout,
            )
            response.raise_for_status()
        except requests.RequestException as error:
            raise SkyWatchAPIError(
                f"Не удалось выполнить запрос к API: {error}"
            ) from error

        try:
            return response.json()
        except ValueError as error:
            raise InvalidAPIResponseError(
                "API вернул ответ, который не удалось прочитать как JSON."
            ) from error


class NominatimClient(_HTTPJSONClient):
    """Клиент API Nominatim для поиска географических границ страны."""

    base_url = "https://nominatim.openstreetmap.org"

    def fetch(self, country: str) -> BoundingBox:
        """Находит bounding box страны по её названию."""

        if not isinstance(country, str):
            raise TypeError("Название страны должно быть строкой.")

        normalized_country = country.strip()

        if not normalized_country:
            raise ValueError("Название страны не может быть пустым.")

        payload = self._get_json(
            endpoint="/search",
            params={
                "country": normalized_country,
                "format": "jsonv2",
                "limit": 1,
                "featureType": "country",
                "addressdetails": 1,
            },
            headers={
                "Accept": "application/json",
                "User-Agent": "SkyWatch/1.0 (educational project)",
            },
        )

        if not isinstance(payload, list) or not payload:
            raise CountryNotFoundError(
                f"Страна «{normalized_country}» не найдена."
            )

        first_result = payload[0]

        if not isinstance(first_result, dict):
            raise InvalidAPIResponseError(
                "Nominatim вернул некорректный результат поиска."
            )

        raw_bounding_box = first_result.get("boundingbox")

        if (
            not isinstance(raw_bounding_box, list)
            or len(raw_bounding_box) != 4
        ):
            raise InvalidAPIResponseError(
                "В ответе Nominatim отсутствует корректный boundingbox."
            )

        try:
            south, north, west, east = (
                float(value) for value in raw_bounding_box
            )
        except (TypeError, ValueError) as error:
            raise InvalidAPIResponseError(
                "Координаты boundingbox должны быть числами."
            ) from error

        return BoundingBox(
            south_latitude=south,
            north_latitude=north,
            west_longitude=west,
            east_longitude=east,
        )

    def get_country_bounds(self, country: str) -> BoundingBox:
        """Понятный публичный метод для получения границ страны."""

        return self.fetch(country)


class OpenSkyClient(_HTTPJSONClient):
    """Клиент API OpenSky для получения текущих данных о самолётах."""

    base_url = "https://opensky-network.org/api"

    def __init__(
        self,
        session: requests.Session | None = None,
        timeout: int = 15,
        access_token: str | None = None,
    ) -> None:
        super().__init__(session=session, timeout=timeout)
        self._access_token = access_token

    def fetch(self, bounding_box: BoundingBox) -> list[list[Any]]:
        """Получает state vectors самолётов внутри указанной области."""

        if not isinstance(bounding_box, BoundingBox):
            raise TypeError(
                "bounding_box должен быть объектом класса BoundingBox."
            )

        headers = {
            "Accept": "application/json",
        }

        if self._access_token:
            headers["Authorization"] = f"Bearer {self._access_token}"

        payload = self._get_json(
            endpoint="/states/all",
            params=bounding_box.to_opensky_params(),
            headers=headers,
        )

        if not isinstance(payload, dict):
            raise InvalidAPIResponseError(
                "OpenSky вернул ответ в некорректном формате."
            )

        states = payload.get("states")

        if states is None:
            return []

        if not isinstance(states, list):
            raise InvalidAPIResponseError(
                "Поле states в ответе OpenSky должно быть списком."
            )

        return [state for state in states if isinstance(state, list)]

    def get_states(self, bounding_box: BoundingBox) -> list[list[Any]]:
        """Публичный метод получения данных о самолётах."""

        return self.fetch(bounding_box)


class AeroplanesAPI:
    """Объединяет Nominatim и OpenSky."""

    def __init__(
        self,
        nominatim_client: NominatimClient | None = None,
        opensky_client: OpenSkyClient | None = None,
    ) -> None:
        self._nominatim_client = nominatim_client or NominatimClient()
        self._opensky_client = opensky_client or OpenSkyClient()

    def get_aeroplanes(self, country: str) -> list[Aeroplane]:
        """Возвращает список самолётов над указанной страной."""

        bounding_box = self._nominatim_client.get_country_bounds(country)

        states = self._opensky_client.get_states(bounding_box)

        return Aeroplane.cast_to_object_list(states)
