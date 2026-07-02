import pytest

from skywatch.models import Aeroplane
from skywatch.services import AeroplaneService


@pytest.fixture
def aeroplanes() -> list[Aeroplane]:
    return [
        Aeroplane(
            icao24="a1b2c3",
            callsign="SKW101",
            origin_country="Germany",
            velocity=250.5,
            altitude=10_200,
            on_ground=False,
        ),
        Aeroplane(
            icao24="d4e5f6",
            callsign="SKW202",
            origin_country="France",
            velocity=210.0,
            altitude=8_500,
            on_ground=True,
        ),
        Aeroplane(
            icao24="1a2b3c",
            callsign="SKW303",
            origin_country="Germany",
            velocity=None,
            altitude=12_500,
            on_ground=False,
        ),
        Aeroplane(
            icao24="4d5e6f",
            callsign="SKW404",
            origin_country="Italy",
            velocity=300.0,
            altitude=None,
            on_ground=False,
        ),
    ]


def test_sort_by_altitude_places_highest_aeroplane_first(
    aeroplanes: list[Aeroplane],
) -> None:
    result = AeroplaneService.sort_by_altitude(aeroplanes)

    assert result[0].icao24 == "1a2b3c"
    assert result[-1].icao24 == "4d5e6f"


def test_sort_by_velocity_places_fastest_aeroplane_first(
    aeroplanes: list[Aeroplane],
) -> None:
    result = AeroplaneService.sort_by_velocity(aeroplanes)

    assert result[0].icao24 == "4d5e6f"
    assert result[-1].icao24 == "1a2b3c"


def test_get_top_by_altitude_returns_requested_number(
    aeroplanes: list[Aeroplane],
) -> None:
    result = AeroplaneService.get_top_by_altitude(aeroplanes, 2)

    assert len(result) == 2
    assert result[0].icao24 == "1a2b3c"
    assert result[1].icao24 == "a1b2c3"


def test_get_top_by_velocity_returns_requested_number(
    aeroplanes: list[Aeroplane],
) -> None:
    result = AeroplaneService.get_top_by_velocity(aeroplanes, 2)

    assert len(result) == 2
    assert result[0].icao24 == "4d5e6f"
    assert result[1].icao24 == "a1b2c3"


def test_filter_by_origin_country_is_case_insensitive(
    aeroplanes: list[Aeroplane],
) -> None:
    result = AeroplaneService.filter_by_origin_country(
        aeroplanes,
        "germany",
    )

    assert len(result) == 2
    assert {aeroplane.icao24 for aeroplane in result} == {
        "a1b2c3",
        "1a2b3c",
    }


def test_filter_by_altitude_range(aeroplanes: list[Aeroplane]) -> None:
    result = AeroplaneService.filter_by_altitude_range(
        aeroplanes,
        8_000,
        11_000,
    )

    assert {aeroplane.icao24 for aeroplane in result} == {
        "a1b2c3",
        "d4e5f6",
    }


def test_filter_by_ground_status(aeroplanes: list[Aeroplane]) -> None:
    result = AeroplaneService.filter_by_ground_status(
        aeroplanes,
        on_ground=True,
    )

    assert len(result) == 1
    assert result[0].icao24 == "d4e5f6"


def test_get_statistics(aeroplanes: list[Aeroplane]) -> None:
    statistics = AeroplaneService.get_statistics(aeroplanes)

    assert statistics.total_count == 4
    assert statistics.airborne_count == 3
    assert statistics.grounded_count == 1
    assert statistics.average_altitude == pytest.approx(10_400)
    assert statistics.average_velocity == pytest.approx(253.5)
    assert statistics.highest_aeroplane is not None
    assert statistics.highest_aeroplane.icao24 == "1a2b3c"
    assert statistics.fastest_aeroplane is not None
    assert statistics.fastest_aeroplane.icao24 == "4d5e6f"
    assert statistics.countries_count == {
        "Germany": 2,
        "France": 1,
        "Italy": 1,
    }


def test_get_top_rejects_zero_limit(aeroplanes: list[Aeroplane]) -> None:
    with pytest.raises(ValueError):
        AeroplaneService.get_top_by_altitude(aeroplanes, 0)


def test_altitude_range_rejects_invalid_bounds(
    aeroplanes: list[Aeroplane],
) -> None:
    with pytest.raises(ValueError):
        AeroplaneService.filter_by_altitude_range(
            aeroplanes,
            10_000,
            5_000,
        )


def test_altitude_range_rejects_non_finite_bound(
    aeroplanes: list[Aeroplane],
) -> None:
    with pytest.raises(ValueError, match="конечным числом"):
        AeroplaneService.filter_by_altitude_range(
            aeroplanes,
            float("nan"),
            5_000,
        )


def test_sort_rejects_non_boolean_direction(
    aeroplanes: list[Aeroplane],
) -> None:
    with pytest.raises(TypeError, match="descending"):
        AeroplaneService.sort_by_altitude(
            aeroplanes,
            descending=1,  # type: ignore[arg-type]
        )
