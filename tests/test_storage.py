import json
from pathlib import Path

import pytest

from skywatch.models import Aeroplane
from skywatch.storage import JSONSaver, StorageDataError, StorageError


@pytest.fixture
def first_aeroplane() -> Aeroplane:
    return Aeroplane(
        icao24="a1b2c3",
        callsign="SKW101",
        origin_country="Germany",
        velocity=250.5,
        altitude=10_200,
        on_ground=False,
    )


@pytest.fixture
def second_aeroplane() -> Aeroplane:
    return Aeroplane(
        icao24="d4e5f6",
        callsign="SKW202",
        origin_country="France",
        velocity=210.0,
        altitude=8_500,
        on_ground=True,
    )


@pytest.fixture
def storage(tmp_path: Path) -> JSONSaver:
    file_path = tmp_path / "aeroplanes.json"
    return JSONSaver(file_path)


def test_storage_creates_empty_json_file(
    storage: JSONSaver,
    tmp_path: Path,
) -> None:
    file_path = tmp_path / "aeroplanes.json"

    assert file_path.exists()
    assert json.loads(file_path.read_text(encoding="utf-8")) == []


def test_storage_adds_and_returns_aeroplane(
    storage: JSONSaver,
    first_aeroplane: Aeroplane,
) -> None:
    storage.add_aeroplane(first_aeroplane)

    aeroplanes = storage.get_all_aeroplanes()

    assert len(aeroplanes) == 1
    assert aeroplanes[0].icao24 == "a1b2c3"
    assert aeroplanes[0].callsign == "SKW101"


def test_storage_updates_aeroplane_with_same_icao24(
    storage: JSONSaver,
    first_aeroplane: Aeroplane,
) -> None:
    storage.add_aeroplane(first_aeroplane)

    updated_aeroplane = Aeroplane(
        icao24="a1b2c3",
        callsign="SKW999",
        origin_country="Germany",
        velocity=280.0,
        altitude=11_000,
    )

    storage.add_aeroplane(updated_aeroplane)

    aeroplanes = storage.get_all_aeroplanes()

    assert len(aeroplanes) == 1
    assert aeroplanes[0].callsign == "SKW999"
    assert aeroplanes[0].velocity == 280.0


def test_storage_filters_aeroplanes_by_country(
    storage: JSONSaver,
    first_aeroplane: Aeroplane,
    second_aeroplane: Aeroplane,
) -> None:
    storage.add_aeroplane(first_aeroplane)
    storage.add_aeroplane(second_aeroplane)

    german_aeroplanes = storage.get_aeroplanes(
        origin_country="germany",
    )

    assert len(german_aeroplanes) == 1
    assert german_aeroplanes[0].icao24 == "a1b2c3"


def test_storage_filters_aeroplanes_by_ground_status(
    storage: JSONSaver,
    first_aeroplane: Aeroplane,
    second_aeroplane: Aeroplane,
) -> None:
    storage.add_aeroplane(first_aeroplane)
    storage.add_aeroplane(second_aeroplane)

    grounded_aeroplanes = storage.get_aeroplanes(on_ground=True)

    assert len(grounded_aeroplanes) == 1
    assert grounded_aeroplanes[0].icao24 == "d4e5f6"


def test_storage_deletes_aeroplane(
    storage: JSONSaver,
    first_aeroplane: Aeroplane,
) -> None:
    storage.add_aeroplane(first_aeroplane)

    result = storage.delete_aeroplane(first_aeroplane)

    assert result is True
    assert storage.get_all_aeroplanes() == []


def test_storage_returns_false_when_deleting_missing_aeroplane(
    storage: JSONSaver,
    first_aeroplane: Aeroplane,
) -> None:
    result = storage.delete_aeroplane(first_aeroplane)

    assert result is False


def test_storage_raises_error_for_invalid_json(tmp_path: Path) -> None:
    file_path = tmp_path / "broken.json"
    file_path.write_text("{invalid json", encoding="utf-8")

    storage = JSONSaver.__new__(JSONSaver)
    storage._file_path = file_path

    with pytest.raises(StorageDataError):
        storage.get_all_aeroplanes()


def test_storage_wraps_directory_creation_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def raise_permission_error(*args: object, **kwargs: object) -> None:
        raise PermissionError("access denied")

    monkeypatch.setattr(Path, "mkdir", raise_permission_error)

    with pytest.raises(StorageError, match="Не удалось создать каталог"):
        JSONSaver(tmp_path / "unavailable" / "aeroplanes.json")
