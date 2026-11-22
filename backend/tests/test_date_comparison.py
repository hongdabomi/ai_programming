from pathlib import Path
from typing import Literal

import pytest
from fastapi.testclient import TestClient

from backend.app import date_meal_sheet_storage, meal_sheet_storage, profile_storage
from backend.app.date_meal_sheet_storage import (
    DateMealMenu,
    MealType,
    StoredMealSheetStatus,
)
from backend.app.main import app


@pytest.fixture(autouse=True)
def comparison_files(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    date_path = tmp_path / "data" / "meal_sheets.json"
    legacy_path = tmp_path / "data" / "meal_sheet.json"
    monkeypatch.setattr(
        date_meal_sheet_storage, "MEAL_SHEETS_FILE", date_path
    )
    monkeypatch.setattr(
        date_meal_sheet_storage, "LEGACY_MEAL_SHEET_FILE", legacy_path
    )
    monkeypatch.setattr(meal_sheet_storage, "MEAL_SHEET_FILE", legacy_path)
    monkeypatch.setattr(
        profile_storage, "PROFILE_FILE", tmp_path / "data" / "profile.json"
    )


def menu(
    menu_id: str,
    name: str,
    allergens: list[str] | None,
    meal_type: MealType | None = None,
) -> DateMealMenu:
    return {
        "id": menu_id,
        "name": name,
        "allergens": allergens,
        "is_information_complete": True,
        "meal_type": meal_type,
    }


def save_sheet(
    selected_date: str,
    status: StoredMealSheetStatus,
    menus: list[DateMealMenu],
) -> None:
    date_meal_sheet_storage.save_date_meal_sheet(
        selected_date,
        status,
        menus,
        replace_existing=False,
    )


def test_analysis_uses_only_all_reviewed_menus_from_the_selected_date() -> None:
    profile_storage.save_profile(["우유"])
    save_sheet(
        "2026-11-24",
        "REVIEWED",
        [
            menu("selected-morning", "우유죽", ["우유"], "morning_snack"),
            menu("selected-lunch", "밀국수", ["밀"], "lunch"),
        ],
    )
    save_sheet(
        "2026-11-25",
        "REVIEWED",
        [menu("other-date", "두유", ["대두"], "lunch")],
    )

    with TestClient(app) as client:
        selected = client.post("/api/meal-sheets/2026-11-24/analyze")
        other = client.post("/api/meal-sheets/2026-11-25/analyze")

    assert selected.status_code == 200
    selected_payload = selected.json()
    assert selected_payload["date"] == "2026-11-24"
    assert [result["menu_id"] for result in selected_payload["results"]] == [
        "selected-morning",
        "selected-lunch",
    ]
    assert [result["status"] for result in selected_payload["results"]] == [
        "MATCH",
        "NOT_IDENTIFIED",
    ]
    assert selected_payload["results"][0]["evidence"] == ["우유"]
    assert "섭취 안전을 보장하지 않습니다" in selected_payload["results"][1][
        "reason"
    ]
    assert other.status_code == 200
    assert other.json()["date"] == "2026-11-25"
    assert [result["menu_id"] for result in other.json()["results"]] == [
        "other-date"
    ]
    assert other.json()["results"][0]["status"] == "NOT_IDENTIFIED"


@pytest.mark.parametrize(
    ("status", "menus", "expected_detail"),
    [
        (
            "NO_DATA",
            None,
            "선택한 날짜에 저장된 급식 정보가 없습니다.",
        ),
        (
            "DRAFT",
            [menu("draft", "검토 전 메뉴", ["우유"])],
            "선택한 날짜의 메뉴를 검토 완료로 저장한 뒤 비교해 주세요.",
        ),
        (
            "NO_MEAL",
            [],
            "선택한 날짜는 급식 없음으로 확인되어 비교할 메뉴가 없습니다.",
        ),
    ],
)
def test_non_reviewed_date_states_do_not_return_comparison_results(
    status: Literal["NO_DATA", "DRAFT", "NO_MEAL"],
    menus: list[DateMealMenu] | None,
    expected_detail: str,
) -> None:
    profile_storage.save_profile(["우유"])
    selected_date = "2026-11-24"
    if menus is not None:
        if status == "NO_MEAL":
            save_sheet(selected_date, "NO_MEAL", menus)
        else:
            save_sheet(selected_date, "DRAFT", menus)

    with TestClient(app) as client:
        response = client.post(f"/api/meal-sheets/{selected_date}/analyze")

    assert response.status_code == 409
    assert response.json()["detail"] == expected_detail


def test_date_analysis_requires_registered_allergies() -> None:
    save_sheet(
        "2026-11-24",
        "REVIEWED",
        [menu("m1", "우유죽", ["우유"])],
    )

    with TestClient(app) as client:
        response = client.post("/api/meal-sheets/2026-11-24/analyze")

    assert response.status_code == 409
    assert response.json()["detail"] == "먼저 알레르기 정보를 등록해 주세요."
