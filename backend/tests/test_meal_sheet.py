import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.app import meal_sheet_storage, profile_storage
from backend.app.main import app


@pytest.fixture
def meal_sheet_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    path = tmp_path / "data" / "meal_sheet.json"
    monkeypatch.setattr(meal_sheet_storage, "MEAL_SHEET_FILE", path)
    return path


@pytest.fixture
def profile_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    path = tmp_path / "data" / "profile.json"
    monkeypatch.setattr(profile_storage, "PROFILE_FILE", path)
    return path


def menu(
    menu_id: str = "m1",
    name: str = "우유 수프",
    allergens: list[str] | None = None,
    is_information_complete: bool = True,
) -> dict[str, object]:
    return {
        "id": menu_id,
        "name": name,
        "allergens": allergens if allergens is not None else ["우유"],
        "is_information_complete": is_information_complete,
    }


def test_current_meal_sheet_defaults_to_empty_draft(
    meal_sheet_file: Path,
) -> None:
    with TestClient(app) as client:
        response = client.get("/api/meal-sheets/current")

    assert response.status_code == 200
    assert response.json() == {
        "source": "manual",
        "reviewed": False,
        "menus": [],
    }
    assert not meal_sheet_file.exists()


def test_meal_sheet_is_saved_and_loaded_after_a_new_request(
    meal_sheet_file: Path,
) -> None:
    payload = {
        "reviewed": False,
        "menus": [
            menu("m1", "  우유 수프  ", ["우유", "대두"]),
            menu("m2", "채소국", [], False),
        ],
    }

    with TestClient(app) as client:
        saved = client.put("/api/meal-sheets/current", json=payload)

    assert saved.status_code == 200
    assert saved.json() == {
        "source": "manual",
        "reviewed": False,
        "menus": [
            menu("m1", "우유 수프", ["우유", "대두"]),
            menu("m2", "채소국", [], False),
        ],
    }
    stored = json.loads(meal_sheet_file.read_text(encoding="utf-8"))
    assert stored["menus"][0]["name"] == "우유 수프"

    with TestClient(app) as client:
        loaded = client.get("/api/meal-sheets/current")

    assert loaded.status_code == 200
    assert loaded.json() == saved.json()


def test_meal_sheet_put_updates_and_removes_menus(meal_sheet_file: Path) -> None:
    with TestClient(app) as client:
        client.put(
            "/api/meal-sheets/current",
            json={
                "reviewed": False,
                "menus": [menu("m1"), menu("m2", "채소국", [], False)],
            },
        )
        updated = client.put(
            "/api/meal-sheets/current",
            json={
                "reviewed": True,
                "menus": [menu("m1", "수정한 우유 수프", ["우유", "대두"])],
            },
        )

    assert updated.status_code == 200
    assert updated.json()["reviewed"] is True
    assert updated.json()["menus"] == [
        menu("m1", "수정한 우유 수프", ["우유", "대두"])
    ]


@pytest.mark.parametrize(
    "payload",
    [
        {
            "reviewed": True,
            "menus": [menu("same"), menu("same", "다른 메뉴")],
        },
        {"reviewed": True, "menus": []},
        {"reviewed": True, "menus": [menu("m1", "   ")]},
    ],
)
def test_meal_sheet_rejects_invalid_reviewed_data(
    meal_sheet_file: Path, payload: dict[str, object]
) -> None:
    with TestClient(app) as client:
        response = client.put("/api/meal-sheets/current", json=payload)

    assert response.status_code == 422
    assert not meal_sheet_file.exists()


def test_meal_sheet_preserves_unrecognized_display_text(
    meal_sheet_file: Path,
) -> None:
    with TestClient(app) as client:
        response = client.put(
            "/api/meal-sheets/current",
            json={
                "reviewed": True,
                "menus": [menu("m1", "메뉴", ["알 수 없는 표시"])],
            },
        )

    assert response.status_code == 200
    assert response.json()["menus"][0]["allergens"] == ["알 수 없는 표시"]


def test_get_reports_corrupt_meal_sheet_json(meal_sheet_file: Path) -> None:
    meal_sheet_file.parent.mkdir(parents=True)
    meal_sheet_file.write_text("{invalid", encoding="utf-8")

    with TestClient(app) as client:
        response = client.get("/api/meal-sheets/current")

    assert response.status_code == 500
    assert response.json()["detail"] == "저장된 급식표 정보를 읽을 수 없습니다."


def test_get_rejects_invalid_meal_sheet_structure(
    meal_sheet_file: Path,
) -> None:
    meal_sheet_file.parent.mkdir(parents=True)
    meal_sheet_file.write_text(
        json.dumps({"source": "manual", "reviewed": True, "menus": []}),
        encoding="utf-8",
    )

    with TestClient(app) as client:
        response = client.get("/api/meal-sheets/current")

    assert response.status_code == 500
    assert response.json()["detail"] == (
        "메뉴를 추가한 뒤 검토 완료로 저장해 주세요."
    )


def test_put_reports_meal_sheet_storage_write_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    blocking_file = tmp_path / "not-a-directory"
    blocking_file.write_text("blocker", encoding="utf-8")
    monkeypatch.setattr(
        meal_sheet_storage,
        "MEAL_SHEET_FILE",
        blocking_file / "meal_sheet.json",
    )

    with TestClient(app) as client:
        response = client.put(
            "/api/meal-sheets/current",
            json={"reviewed": False, "menus": [menu()]},
        )

    assert response.status_code == 500
    assert response.json()["detail"] == "급식표 정보를 저장할 수 없습니다."


def test_analyze_uses_latest_reviewed_saved_values(
    meal_sheet_file: Path, profile_file: Path
) -> None:
    profile_storage.save_profile(["우유"])
    first_sheet = [
        {
            "id": "m1",
            "name": "국수",
            "allergens": ["밀"],
            "is_information_complete": True,
        }
    ]
    meal_sheet_storage.save_meal_sheet(first_sheet, reviewed=True)

    with TestClient(app) as client:
        first_result = client.post(
            "/api/analyze",
            json={
                "menus": [
                    {
                        "id": "unreviewed",
                        "name": "우유 수프",
                        "allergens": ["우유"],
                        "is_information_complete": True,
                    }
                ]
            },
        )
        saved = client.put(
            "/api/meal-sheets/current",
            json={
                "reviewed": True,
                "menus": [
                    menu(
                        "m1",
                        "수정한 우유 수프",
                        ["우유"],
                    )
                ],
            },
        )
        updated_result = client.post("/api/analyze")

    assert first_result.status_code == 200
    assert first_result.json()["results"][0]["status"] == "NOT_IDENTIFIED"
    assert first_result.json()["results"][0]["menu_name"] == "국수"
    assert saved.status_code == 200
    assert updated_result.status_code == 200
    result = updated_result.json()["results"][0]
    assert result["status"] == "MATCH"
    assert result["menu_name"] == "수정한 우유 수프"
    assert result["evidence"] == ["우유"]
