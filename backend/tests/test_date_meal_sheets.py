import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.app import date_meal_sheet_storage, meal_sheet_storage
from backend.app.main import app


@pytest.fixture
def meal_sheet_files(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> tuple[Path, Path]:
    date_path = tmp_path / "data" / "meal_sheets.json"
    legacy_path = tmp_path / "data" / "meal_sheet.json"
    monkeypatch.setattr(
        date_meal_sheet_storage, "MEAL_SHEETS_FILE", date_path
    )
    monkeypatch.setattr(
        date_meal_sheet_storage, "LEGACY_MEAL_SHEET_FILE", legacy_path
    )
    monkeypatch.setattr(meal_sheet_storage, "MEAL_SHEET_FILE", legacy_path)
    return date_path, legacy_path


def menu(
    menu_id: str = "m1",
    name: str = "우유 수프",
    meal_type: str | None = None,
) -> dict[str, object]:
    return {
        "id": menu_id,
        "name": name,
        "allergens": ["우유"],
        "is_information_complete": True,
        "meal_type": meal_type,
    }


def date_payload(
    status: str, menus: list[dict[str, object]], replace_existing: bool = False
) -> dict[str, object]:
    return {
        "status": status,
        "menus": menus,
        "replace_existing": replace_existing,
    }


def test_missing_date_is_information_unavailable_without_creating_data_file(
    meal_sheet_files: tuple[Path, Path],
) -> None:
    date_path, _ = meal_sheet_files

    with TestClient(app) as client:
        response = client.get("/api/meal-sheets/2026-11-24")
        month = client.get("/api/meal-sheets?month=2026-11")

    assert response.status_code == 200
    assert response.json() == {
        "date": "2026-11-24",
        "status": "NO_DATA",
        "source": "manual",
        "service_status": None,
        "reviewed": False,
        "menus": [],
    }
    assert month.status_code == 200
    assert month.json() == {"month": "2026-11", "sheets": []}
    assert not date_path.exists()


def test_dates_store_optional_meal_type_and_reload_independently(
    meal_sheet_files: tuple[Path, Path],
) -> None:
    date_path, _ = meal_sheet_files
    first_date = "2026-11-24"
    second_date = "2026-11-25"

    with TestClient(app) as client:
        saved = client.put(
            f"/api/meal-sheets/{first_date}",
            json=date_payload("DRAFT", [menu(meal_type=None)]),
        )
        second = client.put(
            f"/api/meal-sheets/{second_date}",
            json=date_payload(
                "REVIEWED", [menu("m2", "채소국", "lunch")]
            ),
        )
        next_month = client.put(
            "/api/meal-sheets/2026-12-01",
            json=date_payload("DRAFT", [menu("m3", "다음 달 메뉴")]),
        )
        loaded = client.get(f"/api/meal-sheets/{first_date}")
        month = client.get("/api/meal-sheets?month=2026-11")

    assert saved.status_code == 200
    assert saved.json()["status"] == "DRAFT"
    assert saved.json()["menus"][0]["meal_type"] is None
    assert second.status_code == 200
    assert second.json()["status"] == "REVIEWED"
    assert next_month.status_code == 200
    assert loaded.json() == saved.json()
    assert [sheet["date"] for sheet in month.json()["sheets"]] == [
        first_date,
        second_date,
    ]
    assert json.loads(date_path.read_text(encoding="utf-8"))["sheets"][
        first_date
    ]["menus"][0]["meal_type"] is None


def test_no_meal_has_a_distinct_status_and_empty_menu_list(
    meal_sheet_files: tuple[Path, Path],
) -> None:
    with TestClient(app) as client:
        response = client.put(
            "/api/meal-sheets/2026-11-26",
            json=date_payload("NO_MEAL", []),
        )
        loaded = client.get("/api/meal-sheets/2026-11-26")

    assert response.status_code == 200
    assert response.json()["status"] == "NO_MEAL"
    assert response.json()["service_status"] == "no_meal"
    assert response.json()["reviewed"] is True
    assert response.json()["menus"] == []
    assert loaded.json() == response.json()


def test_existing_date_requires_explicit_replacement_and_is_preserved(
    meal_sheet_files: tuple[Path, Path],
) -> None:
    path = "/api/meal-sheets/2026-11-24"
    original = date_payload("REVIEWED", [menu()])

    with TestClient(app) as client:
        first = client.put(path, json=original)
        refused = client.put(
            path,
            json=date_payload("DRAFT", [menu("m2", "새 메뉴")]),
        )
        after_refusal = client.get(path)
        replaced = client.put(
            path,
            json=date_payload(
                "DRAFT", [menu("m2", "새 메뉴")], replace_existing=True
            ),
        )

    assert first.status_code == 200
    assert refused.status_code == 409
    assert after_refusal.json() == first.json()
    assert replaced.status_code == 200
    assert replaced.json()["status"] == "DRAFT"
    assert replaced.json()["menus"][0]["name"] == "새 메뉴"


def test_legacy_meal_sheet_is_preserved_without_assigning_a_date(
    meal_sheet_files: tuple[Path, Path],
) -> None:
    date_path, legacy_path = meal_sheet_files
    legacy = {
        "source": "manual",
        "reviewed": True,
        "menus": [
            {
                "id": "legacy-1",
                "name": "가상 메뉴",
                "allergens": ["우유"],
                "is_information_complete": True,
            }
        ],
    }
    legacy_path.parent.mkdir(parents=True)
    original_bytes = json.dumps(
        legacy, ensure_ascii=False, indent=2
    ).encode("utf-8")
    legacy_path.write_bytes(original_bytes)

    with TestClient(app) as client:
        date_response = client.get("/api/meal-sheets/2026-11-24")
        unassigned = client.get("/api/meal-sheets/unassigned")
        legacy_api = client.get("/api/meal-sheets/current")

    assert date_response.status_code == 200
    assert date_response.json()["status"] == "NO_DATA"
    assert unassigned.status_code == 200
    assert unassigned.json()["status"] == "UNASSIGNED"
    assert unassigned.json()["date"] is None
    assert unassigned.json()["menus"][0]["name"] == "가상 메뉴"
    assert legacy_api.status_code == 200
    assert legacy_path.read_bytes() == original_bytes
    assert json.loads(date_path.read_text(encoding="utf-8"))[
        "unassigned_legacy"
    ] == legacy


@pytest.mark.parametrize(
    "payload",
    [
        date_payload("NO_MEAL", [menu()]),
        date_payload("REVIEWED", []),
        date_payload("DRAFT", [menu(meal_type="breakfast")]),
        date_payload("DRAFT", [menu(), menu()]),
    ],
)
def test_invalid_date_sheet_data_is_rejected_without_writing(
    meal_sheet_files: tuple[Path, Path],
    payload: dict[str, object],
) -> None:
    date_path, _ = meal_sheet_files

    with TestClient(app) as client:
        response = client.put("/api/meal-sheets/2026-11-24", json=payload)

    assert response.status_code == 422
    assert not date_path.exists()


def test_corrupt_legacy_json_fails_without_overwriting_it(
    meal_sheet_files: tuple[Path, Path],
) -> None:
    date_path, legacy_path = meal_sheet_files
    legacy_path.parent.mkdir(parents=True)
    legacy_path.write_text("{invalid", encoding="utf-8")

    with TestClient(app) as client:
        response = client.get("/api/meal-sheets/2026-11-24")

    assert response.status_code == 500
    assert not date_path.exists()
    assert legacy_path.read_text(encoding="utf-8") == "{invalid"


def test_corrupt_date_store_is_reported_as_storage_error(
    meal_sheet_files: tuple[Path, Path],
) -> None:
    date_path, _ = meal_sheet_files
    date_path.parent.mkdir(parents=True)
    date_path.write_text(
        json.dumps(
            {
                "version": 1,
                "sheets": {
                    "2026-11-24": {
                        "status": [],
                        "source": "manual",
                        "service_status": "provided",
                        "reviewed": False,
                        "menus": [],
                    }
                },
                "unassigned_legacy": None,
            }
        ),
        encoding="utf-8",
    )

    with TestClient(app) as client:
        response = client.get("/api/meal-sheets/2026-11-24")

    assert response.status_code == 500
    assert response.json()["detail"] == (
        "저장된 날짜별 급식표 형식이 올바르지 않습니다."
    )


@pytest.mark.parametrize(
    "url",
    [
        "/api/meal-sheets?month=2026-13",
        "/api/meal-sheets?month=0000-11",
        "/api/meal-sheets/2026-02-30",
    ],
)
def test_invalid_month_or_date_is_rejected(
    meal_sheet_files: tuple[Path, Path],
    url: str,
) -> None:
    with TestClient(app) as client:
        response = client.get(url)

    assert response.status_code == 422
