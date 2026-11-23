from pathlib import Path
from time import perf_counter

import pytest
from fastapi.testclient import TestClient

from backend.app import meal_sheet_storage, profile_storage
from backend.app.allergies import ALLERGEN_NUMBER_TO_NAME
from backend.app.comparison import MenuItem, compare_menus
from backend.app.main import app


@pytest.fixture
def profile_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    path = tmp_path / "data" / "profile.json"
    monkeypatch.setattr(profile_storage, "PROFILE_FILE", path)
    return path


@pytest.fixture
def meal_sheet_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    path = tmp_path / "data" / "meal_sheet.json"
    monkeypatch.setattr(meal_sheet_storage, "MEAL_SHEET_FILE", path)
    return path


@pytest.mark.parametrize(
    ("profile_allergies", "menu", "status", "matched", "evidence"),
    [
        pytest.param(
            ["우유"],
            MenuItem("m1", "우유 수프", ("우유",), True),
            "MATCH",
            ["우유"],
            ["우유"],
            id="single-match",
        ),
        pytest.param(
            ["우유", "대두"],
            MenuItem("m2", "두유 메뉴", ("대두", "우유"), True),
            "MATCH",
            ["우유", "대두"],
            ["대두", "우유"],
            id="multiple-matches",
        ),
        pytest.param(
            ["난류(가금류)"],
            MenuItem("m3", "달걀국", ("달걀",), True),
            "MATCH",
            ["난류(가금류)"],
            ["달걀"],
            id="explicit-egg-alias",
        ),
        pytest.param(
            ["우유"],
            MenuItem("m4", "국수", ("밀",), True),
            "NOT_IDENTIFIED",
            [],
            ["밀"],
            id="complete-without-match",
        ),
        pytest.param(
            ["우유"],
            MenuItem("m5", "국수", ("밀",), False),
            "CHECK_NEEDED",
            [],
            ["밀"],
            id="incomplete-display",
        ),
        pytest.param(
            ["우유"],
            MenuItem("m6", "메뉴", None, True),
            "CHECK_NEEDED",
            [],
            [],
            id="missing-allergen-display",
        ),
        pytest.param(
            ["우유"],
            MenuItem("m7", "메뉴", ("알레르기 번호 2",), True),
            "CHECK_NEEDED",
            [],
            ["알레르기 번호 2"],
            id="unrecognized-display",
        ),
        pytest.param(
            ["우유"],
            MenuItem("m8", "우유 메뉴", ("우유", "우유"), True),
            "MATCH",
            ["우유"],
            ["우유"],
            id="duplicate-display",
        ),
        pytest.param(
            ["우유"],
            MenuItem("m9", "우유 메뉴", ("우유", "미확인 표시"), False),
            "MATCH",
            ["우유"],
            ["우유", "미확인 표시"],
            id="match-priority-with-uncertainty",
        ),
        pytest.param(
            ["우유"],
            MenuItem("m10", "표시가 없는 메뉴", (), True),
            "NOT_IDENTIFIED",
            [],
            [],
            id="complete-empty-display",
        ),
        pytest.param(
            ["우유"],
            MenuItem("m11", "", ("밀",), True),
            "CHECK_NEEDED",
            [],
            ["밀"],
            id="missing-menu-name",
        ),
    ],
)
def test_comparison_scenarios(
    profile_allergies: list[str],
    menu: MenuItem,
    status: str,
    matched: list[str],
    evidence: list[str],
) -> None:
    result = compare_menus(profile_allergies, [menu])[0]

    assert result["status"] == status
    assert result["matched_allergens"] == matched
    assert result["evidence"] == evidence
    assert result["reason"]


def test_empty_menu_list_returns_no_results() -> None:
    assert compare_menus(["우유"], []) == []


@pytest.mark.parametrize(
    ("number", "allergen"), sorted(ALLERGEN_NUMBER_TO_NAME.items())
)
def test_explicit_allergen_numbers_match_their_mapped_names(
    number: int, allergen: str
) -> None:
    for label in (str(number), f"{number}. {allergen}"):
        result = compare_menus(
            [allergen],
            [MenuItem("m1", "메뉴", (label,), True)],
        )[0]

        assert result["status"] == "MATCH"
        assert result["matched_allergens"] == [allergen]
        assert result["evidence"] == [label]


@pytest.mark.parametrize("label", ["20", "2. 밀"])
def test_invalid_or_conflicting_allergen_numbers_need_confirmation(
    label: str,
) -> None:
    result = compare_menus(
        ["우유"],
        [MenuItem("m1", "메뉴", (label,), True)],
    )[0]

    assert result["status"] == "CHECK_NEEDED"
    assert result["matched_allergens"] == []


def test_unrecognized_display_is_included_in_the_reason() -> None:
    result = compare_menus(
        ["우유"],
        [MenuItem("m1", "메뉴", ("알레르기 번호 2",), True)],
    )[0]

    assert result["status"] == "CHECK_NEEDED"
    assert result["evidence"] == ["알레르기 번호 2"]
    assert "해석하지 못한 부분" in result["reason"]


def test_no_identified_match_does_not_claim_food_is_safe() -> None:
    result = compare_menus(
        ["우유"],
        [MenuItem("m1", "국수", ("밀",), True)],
    )[0]

    assert result["status"] == "NOT_IDENTIFIED"
    assert "섭취 안전을 보장하지 않습니다" in result["reason"]


@pytest.mark.parametrize(
    ("marking", "expected_status", "expected_match"),
    [
        ("범례 확인 필요: ①⑤⑥⑩⑬", "NOT_IDENTIFIED", []),
        ("①③⑤", "MATCH", ["메밀"]),
        ("1⑤⑥1013", "CHECK_NEEDED", []),
    ],
)
def test_circled_markings_are_checked_against_registered_allergy_only(
    marking: str, expected_status: str, expected_match: list[str]
) -> None:
    result = compare_menus(
        ["메밀"], [MenuItem("m1", "메뉴", (marking,), False)]
    )[0]

    assert result["status"] == expected_status
    assert result["matched_allergens"] == expected_match


def test_twenty_menus_are_compared_within_one_second() -> None:
    menus = [
        MenuItem(
            f"m{index}",
            f"메뉴 {index}",
            ("우유", "대두") if index % 2 else ("밀",),
            True,
        )
        for index in range(20)
    ]

    started = perf_counter()
    results = compare_menus(["우유", "대두"], menus)
    elapsed = perf_counter() - started

    assert len(results) == 20
    assert elapsed < 1


def test_analyze_api_uses_saved_profile_and_reviewed_meal_sheet(
    profile_file: Path, meal_sheet_file: Path
) -> None:
    profile_storage.save_profile(["우유", "대두"])
    meal_sheet_storage.save_meal_sheet(
        [
            {
                "id": "m1",
                "name": "우유 수프",
                "allergens": ["우유"],
                "is_information_complete": True,
            }
        ],
        reviewed=True,
    )

    with TestClient(app) as client:
        response = client.post("/api/analyze")

    assert response.status_code == 200
    result = response.json()["results"][0]
    assert result["status"] == "MATCH"
    assert result["matched_allergens"] == ["우유"]
    assert result["evidence"] == ["우유"]
    assert response.json()["disclaimer"]


def test_analyze_api_requires_registered_allergies(
    profile_file: Path, meal_sheet_file: Path
) -> None:
    with TestClient(app) as client:
        response = client.post("/api/analyze")

    assert response.status_code == 409
    assert response.json()["detail"] == "먼저 알레르기 정보를 등록해 주세요."


def test_analyze_api_requires_a_reviewed_meal_sheet(
    profile_file: Path, meal_sheet_file: Path
) -> None:
    profile_storage.save_profile(["우유"])
    meal_sheet_storage.save_meal_sheet(
        [
            {
                "id": "m1",
                "name": "우유 수프",
                "allergens": ["우유"],
                "is_information_complete": True,
            }
        ],
        reviewed=False,
    )

    with TestClient(app) as client:
        response = client.post("/api/analyze")

    assert response.status_code == 409
    assert response.json()["detail"] == (
        "급식 메뉴를 검토 완료로 저장한 뒤 비교해 주세요."
    )


def test_analyze_api_reports_corrupt_profile(profile_file: Path) -> None:
    profile_file.parent.mkdir(parents=True)
    profile_file.write_text("{invalid", encoding="utf-8")

    with TestClient(app) as client:
        response = client.post("/api/analyze")

    assert response.status_code == 500
    assert response.json()["detail"] == (
        "저장된 알레르기 정보 파일을 읽을 수 없습니다."
    )


def test_analyze_api_allows_frontend_cors_preflight() -> None:
    with TestClient(app) as client:
        response = client.options(
            "/api/analyze",
            headers={
                "Origin": "http://127.0.0.1:5500",
                "Access-Control-Request-Method": "POST",
            },
        )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == (
        "http://127.0.0.1:5500"
    )
    assert "POST" in response.headers["access-control-allow-methods"]
