import pytest

from skywatch.models import Aeroplane


@pytest.fixture
def first_aeroplane() -> Aeroplane:
    return Aeroplane(
        icao24="a1b2c3",
        callsign="SKW101",
        origin_country="Germany",
        velocity=250.5,
        altitude=10_200,
        longitude=13.4,
        latitude=52.5,
        on_ground=False,
        heading=180,
        vertical_rate=5.2,
        last_contact=1_700_000_000,
    )


@pytest.fixture
def second_aeroplane() -> Aeroplane:
    return Aeroplane(
        icao24="d4e5f6",
        callsign="SKW202",
        origin_country="France",
        velocity=210.0,
        altitude=8_500,
    )


def test_aeroplane_is_created_with_valid_data(
    first_aeroplane: Aeroplane,
) -> None:
    assert first_aeroplane.icao24 == "a1b2c3"
    assert first_aeroplane.callsign == "SKW101"
    assert first_aeroplane.velocity == 250.5
    assert first_aeroplane.altitude == 10_200.0


def test_aeroplane_rejects_invalid_icao24() -> None:
    with pytest.raises(ValueError):
        Aeroplane(
            icao24="invalid",
            callsign="TEST",
            origin_country="Russia",
            velocity=100,
            altitude=1000,
        )


def test_aeroplane_rejects_negative_velocity() -> None:
    with pytest.raises(ValueError):
        Aeroplane(
            icao24="a1b2c3",
            callsign="TEST",
            origin_country="Russia",
            velocity=-1,
            altitude=1000,
        )


def test_aeroplane_rejects_non_finite_velocity() -> None:
    with pytest.raises(ValueError, match="конечным числом"):
        Aeroplane(
            icao24="a1b2c3",
            callsign="TEST",
            origin_country="Russia",
            velocity=float("nan"),
            altitude=1000,
        )


def test_aeroplane_rejects_boolean_last_contact() -> None:
    with pytest.raises(ValueError, match="неотрицательным целым"):
        Aeroplane(
            icao24="a1b2c3",
            callsign="TEST",
            origin_country="Russia",
            velocity=100,
            altitude=1000,
            last_contact=True,
        )


def test_aeroplanes_are_compared_by_altitude(
    first_aeroplane: Aeroplane,
    second_aeroplane: Aeroplane,
) -> None:
    assert first_aeroplane > second_aeroplane
    assert second_aeroplane < first_aeroplane
    assert first_aeroplane.compare_altitude(second_aeroplane) == 1


def test_aeroplanes_can_be_compared_by_speed(
    first_aeroplane: Aeroplane,
    second_aeroplane: Aeroplane,
) -> None:
    assert first_aeroplane.is_faster_than(second_aeroplane)
    assert first_aeroplane.compare_speed(second_aeroplane) == 1


def test_cast_to_object_list_creates_aeroplane_objects() -> None:
    states = [
        [
            "a1b2c3",
            "SKW101 ",
            "Germany",
            1_700_000_000,
            1_700_000_001,
            13.4,
            52.5,
            10_200.0,
            False,
            250.5,
            180.0,
            5.2,
        ]
    ]

    aeroplanes = Aeroplane.cast_to_object_list(states)

    assert len(aeroplanes) == 1
    assert aeroplanes[0].callsign == "SKW101"
    assert aeroplanes[0].altitude == 10_200.0
