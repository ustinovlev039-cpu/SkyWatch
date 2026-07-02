import inspect
from typing import Any

import pytest

from skywatch.api import (
    AeroplanesAPI,
    BaseAPIClient,
    BoundingBox,
    CountryNotFoundError,
    NominatimClient,
    OpenSkyClient,
)
from skywatch.models import Aeroplane


class FakeResponse:

    def __init__(self, payload: Any) -> None:
        self._payload = payload

    def raise_for_status(self) -> None:
        """Имитирует успешный HTTP-ответ."""

    def json(self) -> Any:
        """Возвращает подготовленный JSON."""

        return self._payload


class FakeSession:

    def __init__(self, responses: list[FakeResponse]) -> None:
        self.responses = responses
        self.calls: list[dict[str, Any]] = []

    def get(self, url: str, **kwargs: Any) -> FakeResponse:
        self.calls.append(
            {
                "url": url,
                **kwargs,
            }
        )

        return self.responses.pop(0)


class StubNominatimClient:

    def get_country_bounds(self, country: str) -> BoundingBox:
        assert country == "Spain"

        return BoundingBox(
            south_latitude=36.0,
            north_latitude=43.8,
            west_longitude=-9.4,
            east_longitude=3.4,
        )


class StubOpenSkyClient:

    def get_states(self, bounding_box: BoundingBox) -> list[list[Any]]:
        assert bounding_box.south_latitude == 36.0

        return [
            [
                "a1b2c3",
                "SKW101 ",
                "Spain",
                1_700_000_000,
                1_700_000_001,
                -3.7,
                40.4,
                10_500.0,
                False,
                248.5,
                180.0,
                2.3,
            ]
        ]


def test_base_api_client_contains_only_abstract_methods() -> None:
    methods = [
        value
        for value in BaseAPIClient.__dict__.values()
        if inspect.isfunction(value)
    ]

    assert inspect.isabstract(BaseAPIClient)
    assert methods
    assert all(
        getattr(method, "__isabstractmethod__", False)
        for method in methods
    )


def test_nominatim_rejects_non_string_country() -> None:
    client = NominatimClient(session=FakeSession([]))

    with pytest.raises(TypeError, match="должно быть строкой"):
        client.get_country_bounds(None)  # type: ignore[arg-type]


def test_api_client_rejects_invalid_timeout() -> None:
    with pytest.raises(ValueError, match="больше нуля"):
        NominatimClient(timeout=0)


def test_bounding_box_rejects_non_finite_coordinate() -> None:
    with pytest.raises(ValueError, match="конечным числом"):
        BoundingBox(
            south_latitude=float("nan"),
            north_latitude=43.8,
            west_longitude=-9.4,
            east_longitude=3.4,
        )


def test_nominatim_returns_country_bounding_box() -> None:
    session = FakeSession(
        responses=[
            FakeResponse(
                [
                    {
                        "boundingbox": [
                            "36.0000",
                            "43.8000",
                            "-9.4000",
                            "3.4000",
                        ]
                    }
                ]
            )
        ]
    )

    client = NominatimClient(session=session)
    bounding_box = client.get_country_bounds("Spain")

    assert bounding_box.south_latitude == 36.0
    assert bounding_box.north_latitude == 43.8
    assert bounding_box.west_longitude == -9.4
    assert bounding_box.east_longitude == 3.4

    assert session.calls[0]["params"]["country"] == "Spain"
    assert session.calls[0]["params"]["featureType"] == "country"


def test_nominatim_raises_error_when_country_not_found() -> None:
    session = FakeSession(
        responses=[
            FakeResponse([])
        ]
    )

    client = NominatimClient(session=session)

    with pytest.raises(CountryNotFoundError):
        client.get_country_bounds("UnknownCountry")


def test_opensky_returns_state_vectors() -> None:
    session = FakeSession(
        responses=[
            FakeResponse(
                {
                    "time": 1_700_000_000,
                    "states": [
                        [
                            "a1b2c3",
                            "SKW101 ",
                            "Spain",
                            1_700_000_000,
                            1_700_000_001,
                            -3.7,
                            40.4,
                            10_500.0,
                            False,
                            248.5,
                            180.0,
                            2.3,
                        ]
                    ],
                }
            )
        ]
    )

    bounding_box = BoundingBox(
        south_latitude=36.0,
        north_latitude=43.8,
        west_longitude=-9.4,
        east_longitude=3.4,
    )

    client = OpenSkyClient(
        session=session,
        access_token="test-access-token",
    )

    states = client.get_states(bounding_box)

    assert len(states) == 1
    assert states[0][0] == "a1b2c3"

    assert session.calls[0]["params"] == {
        "lamin": 36.0,
        "lomin": -9.4,
        "lamax": 43.8,
        "lomax": 3.4,
    }

    assert session.calls[0]["headers"]["Authorization"] == (
        "Bearer test-access-token"
    )


def test_aeroplanes_api_returns_aeroplane_objects() -> None:
    api = AeroplanesAPI(
        nominatim_client=StubNominatimClient(),
        opensky_client=StubOpenSkyClient(),
    )

    aeroplanes = api.get_aeroplanes("Spain")

    assert len(aeroplanes) == 1
    assert isinstance(aeroplanes[0], Aeroplane)
    assert aeroplanes[0].callsign == "SKW101"
    assert aeroplanes[0].origin_country == "Spain"
    assert aeroplanes[0].altitude == 10_500.0
