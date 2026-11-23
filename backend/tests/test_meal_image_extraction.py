import base64
import json
from datetime import date
from io import BytesIO
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from backend.app import ai, date_meal_sheet_storage, meal_sheet_storage, profile_storage
from backend.app.allergies import ALLERGEN_NUMBER_TO_NAME
from backend.app.main import MAX_IMAGE_BYTES, app
from backend.app.meal_image_extraction import (
    ExtractedLegendEntry,
    ExtractedMeal,
    GeminiMealExtraction,
    build_image_extraction_response,
)


@pytest.fixture
def extraction_files(
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
    monkeypatch.setattr(
        profile_storage, "PROFILE_FILE", tmp_path / "data" / "profile.json"
    )
    return date_path, legacy_path


def png_bytes() -> bytes:
    output = BytesIO()
    Image.new("RGB", (4, 4), color="white").save(output, format="PNG")
    return output.getvalue()


def post_image(
    client: TestClient,
    *,
    scope: str = "daily",
    selected_date: str | None = "2026-11-24",
    reference_date: str | None = "2026-11-24",
    reference_month: str | None = None,
    filename: str = "meal.png",
    content: bytes | None = None,
    content_type: str = "image/png",
):
    data = {"scope": scope}
    if selected_date is not None:
        data["selected_date"] = selected_date
    if reference_date is not None:
        data["reference_date"] = reference_date
    if reference_month is not None:
        data["reference_month"] = reference_month
    return client.post(
        "/api/meal-sheets/extract",
        data=data,
        files={
            "image": (
                filename,
                png_bytes() if content is None else content,
                content_type,
            )
        },
    )


def candidate(
    *,
    date_text: str | None = "2026-11-24",
    date_iso: str | None = "2026-11-24",
    date_has_explicit_year: bool = True,
    name: str = "우유죽",
    meal_type: str | None = None,
    allergen_marking: str | None = "(2)",
    legend_present: bool = False,
    legend_readable: bool = True,
    legend_entries: list[ExtractedLegendEntry] | None = None,
) -> GeminiMealExtraction:
    return GeminiMealExtraction(
        menus=[
            ExtractedMeal(
                date_text=date_text,
                date_iso=date_iso,
                date_has_explicit_year=date_has_explicit_year,
                name=name,
                meal_type=meal_type,
                allergen_marking=allergen_marking,
            )
        ],
        legend_present=legend_present,
        legend_readable=legend_readable,
        legend_entries=legend_entries or [],
    )


def mock_extraction(
    monkeypatch: pytest.MonkeyPatch,
    result: GeminiMealExtraction,
) -> None:
    def extract(
        image_bytes: bytes, mime_type: str, scope: str, selected_date: date
    ) -> GeminiMealExtraction:
        assert image_bytes
        assert mime_type == "image/png"
        assert scope in {"daily", "monthly"}
        assert selected_date == date(2026, 11, 24)
        return result

    monkeypatch.setattr(ai, "extract_meal_menus", extract)


def test_daily_image_returns_unreviewed_candidate_without_saving(
    extraction_files: tuple[Path, Path],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    date_path, _ = extraction_files
    mock_extraction(
        monkeypatch,
        candidate(
            name="우유죽",
            meal_type=None,
            allergen_marking="①⑤",
        ),
    )

    with TestClient(app) as client:
        response = post_image(client)

    assert response.status_code == 200
    payload = response.json()
    assert payload["source"] == "uploaded-image"
    assert payload["reviewed"] is False
    assert payload["scope"] == "daily"
    assert payload["selected_date"] == "2026-11-24"
    assert payload["reference_date"] == "2026-11-24"
    assert payload["menus"][0]["date"] == "2026-11-24"
    assert payload["menus"][0]["meal_type"] is None
    assert payload["menus"][0]["allergen_numbers"] == [1, 5]
    assert payload["menus"][0]["allergens"] == [
        ALLERGEN_NUMBER_TO_NAME[1],
        ALLERGEN_NUMBER_TO_NAME[5],
    ]
    assert payload["menus"][0]["is_information_complete"] is False
    assert not date_path.exists()


def test_undated_daily_image_keeps_menu_as_unassigned_candidate() -> None:
    extraction = candidate(
        date_text=None,
        date_iso=None,
        date_has_explicit_year=False,
        name="날짜 없는 메뉴",
    )

    result = build_image_extraction_response(
        extraction, "daily", date(2026, 11, 24), date(2026, 11, 24), None
    )

    assert len(result.menus) == 1
    assert result.menus[0].date is None
    assert result.menus[0].date_requires_confirmation is True


def test_monthly_image_returns_only_the_selected_date_and_keeps_year_unknown(
    extraction_files: tuple[Path, Path],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    extraction = GeminiMealExtraction(
        menus=[
            ExtractedMeal(
                date_text="2026년 11월 24일",
                date_iso="2026-11-24",
                date_has_explicit_year=True,
                name="우유죽",
                allergen_marking="(2)",
            ),
            ExtractedMeal(
                date_text="2026년 11월 25일",
                date_iso="2026-11-25",
                date_has_explicit_year=True,
                name="두유",
                meal_type="lunch",
                allergen_marking="(5)",
            ),
            ExtractedMeal(
                date_text="11/??",
                date_iso=None,
                date_has_explicit_year=False,
                name="읽기 어려운 메뉴",
                allergen_marking=None,
            ),
            ExtractedMeal(
                date_text="11/24",
                date_iso=None,
                date_has_explicit_year=False,
                name="연도 미표기 메뉴",
                allergen_marking="(2)",
            ),
        ]
    )
    mock_extraction(monkeypatch, extraction)

    with TestClient(app) as client:
        response = post_image(
            client,
            scope="monthly",
            reference_date=None,
            reference_month="2026-11",
            selected_date="2026-11-24",
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["scope"] == "monthly"
    assert payload["selected_date"] == "2026-11-24"
    assert [item["date"] for item in payload["menus"]] == [
        "2026-11-24",
        None,
    ]
    assert payload["menus"][1]["date_text"] == "11/24"
    assert payload["menus"][1]["date_requires_confirmation"] is True
    assert payload["menus"][1]["is_information_complete"] is False
    assert "급식 없음" not in payload["extraction_warnings"][0]


@pytest.mark.parametrize(
    "date_text",
    ["2026년 11월 식단표 / 24(화)", "24(화)"],
)
def test_monthly_calendar_header_date_is_kept_for_selected_day(
    date_text: str,
) -> None:
    extraction = candidate(
        date_text=date_text,
        date_iso="2026-11-24",
        date_has_explicit_year=True,
        name="흑미밥",
    )

    selected = build_image_extraction_response(
        extraction, "monthly", date(2026, 11, 24), None, "2026-11"
    )
    other_day = build_image_extraction_response(
        extraction, "monthly", date(2026, 11, 25), None, "2026-11"
    )

    assert [menu.name for menu in selected.menus] == ["흑미밥"]
    assert other_day.menus == []


def test_monthly_image_filters_large_candidate_list_to_selected_date(
    extraction_files: tuple[Path, Path],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    menus = [
        ExtractedMeal(
            date_text="2026년 11월 24일",
            date_iso="2026-11-24",
            date_has_explicit_year=True,
            name="선택 날짜 메뉴",
            allergen_marking="(2)",
        )
    ]
    other_days = [day for day in range(1, 31) if day != 24]
    menus.extend(
        ExtractedMeal(
            date_text=f"2026년 11월 {other_days[index % len(other_days)]}일",
            date_iso=f"2026-11-{other_days[index % len(other_days)]:02d}",
            date_has_explicit_year=True,
            name=f"다른 날짜 메뉴 {index}",
        )
        for index in range(152)
    )
    mock_extraction(monkeypatch, GeminiMealExtraction(menus=menus))

    with TestClient(app) as client:
        response = post_image(
            client,
            scope="monthly",
            reference_date=None,
            reference_month="2026-11",
            selected_date="2026-11-24",
        )

    assert response.status_code == 200
    payload = response.json()
    assert len(payload["menus"]) == 1
    assert payload["menus"][0]["name"] == "선택 날짜 메뉴"
    assert payload["menus"][0]["date"] == "2026-11-24"


def test_monthly_image_without_matching_or_identifiable_date_requests_confirmation(
    extraction_files: tuple[Path, Path],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mock_extraction(
        monkeypatch,
        GeminiMealExtraction(
            menus=[
                ExtractedMeal(
                    date_text=None,
                    date_iso=None,
                    date_has_explicit_year=False,
                    name="날짜를 알 수 없는 메뉴",
                ),
                ExtractedMeal(
                    date_text="2026년 11월 25일",
                    date_iso="2026-11-25",
                    date_has_explicit_year=True,
                    name="다른 날짜 메뉴",
                ),
                ExtractedMeal(
                    date_text="2026년 11월 25일",
                    date_iso="2026-11-24",
                    date_has_explicit_year=True,
                    name="날짜 표기와 정규화 값이 충돌하는 메뉴",
                ),
            ]
        ),
    )

    with TestClient(app) as client:
        response = post_image(
            client,
            scope="monthly",
            reference_date=None,
            reference_month="2026-11",
            selected_date="2026-11-24",
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["menus"] == []
    assert payload["extraction_warnings"]
    assert "급식 없음" in payload["extraction_warnings"][0]


@pytest.mark.parametrize("marking", ["①⑤", "(1.5)", "(1,5)"])
def test_allergen_number_notations_use_explicit_mapping(
    marking: str,
) -> None:
    result = build_image_extraction_response(
        candidate(allergen_marking=marking),
        "daily",
        date(2026, 11, 24),
        date(2026, 11, 24),
        None,
    )

    assert result.menus[0].allergen_numbers == [1, 5]
    assert result.menus[0].allergens == [
        ALLERGEN_NUMBER_TO_NAME[1],
        ALLERGEN_NUMBER_TO_NAME[5],
    ]


def test_image_legend_conflict_requires_confirmation() -> None:
    result = build_image_extraction_response(
        candidate(
            allergen_marking="(2)",
            legend_present=True,
            legend_entries=[
                ExtractedLegendEntry(number=2, label="밀"),
            ],
        ),
        "daily",
        date(2026, 11, 24),
        date(2026, 11, 24),
        None,
    )

    assert result.legend_status == "NEEDS_CONFIRMATION"
    assert result.menus[0].allergens == ["(2)"]
    assert result.menus[0].warnings


def test_unclear_mixed_marking_keeps_original_without_guessing_numbers() -> None:
    result = build_image_extraction_response(
        candidate(
            allergen_marking="1⑤⑥1013",
            legend_present=True,
            legend_readable=False,
        ),
        "daily",
        date(2026, 11, 24),
        date(2026, 11, 24),
        None,
    )

    assert result.legend_status == "NEEDS_CONFIRMATION"
    assert result.menus[0].allergen_numbers == [5, 6]
    assert result.menus[0].allergens == ["1⑤⑥1013"]


def test_image_legend_is_used_only_after_matching_reference_map() -> None:
    result = build_image_extraction_response(
        candidate(
            allergen_marking="(2)",
            legend_present=True,
            legend_entries=[
                ExtractedLegendEntry(number=2, label="우유"),
            ],
        ),
        "daily",
        date(2026, 11, 24),
        date(2026, 11, 24),
        None,
    )

    assert result.legend_status == "VERIFIED"
    assert result.menus[0].allergens == ["우유"]


def test_partial_date_and_unreadable_name_stay_unassigned(
    extraction_files: tuple[Path, Path],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mock_extraction(
        monkeypatch,
        candidate(
            date_text="11/24",
            date_iso="2026-11-24",
            date_has_explicit_year=False,
            name="",
            allergen_marking=None,
        ),
    )

    with TestClient(app) as client:
        response = post_image(client)

    assert response.status_code == 200
    item = response.json()["menus"][0]
    assert item["date"] is None
    assert item["date_text"] == "11/24"
    assert item["name"] == ""
    assert item["allergens"] is None
    assert len(item["warnings"]) >= 3


@pytest.mark.parametrize(
    ("filename", "content_type", "content", "expected_status"),
    [
        pytest.param("menu.pdf", "application/pdf", b"%PDF-1.7", 415, id="unsupported-extension"),
        pytest.param("menu.png", "image/png", b"", 400, id="empty-image"),
        pytest.param("menu.png", "image/png", b"not-an-image", 400, id="invalid-image"),
        pytest.param(
            "menu.png",
            "image/png",
            b"x" * (MAX_IMAGE_BYTES + 1),
            413,
            id="size-limit",
        ),
        pytest.param("menu.png", "image/jpeg", png_bytes(), 415, id="mime-mismatch"),
    ],
)
def test_invalid_image_is_rejected_before_gemini_call(
    extraction_files: tuple[Path, Path],
    monkeypatch: pytest.MonkeyPatch,
    filename: str,
    content_type: str,
    content: bytes,
    expected_status: int,
) -> None:
    def fail_if_called(*args: object, **kwargs: object) -> None:
        raise AssertionError("Gemini must not receive an invalid image.")

    monkeypatch.setattr(ai, "extract_meal_menus", fail_if_called)

    with TestClient(app) as client:
        response = post_image(
            client,
            filename=filename,
            content_type=content_type,
            content=content,
        )

    assert response.status_code == expected_status


def test_image_extraction_requires_a_selected_date(
    extraction_files: tuple[Path, Path],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        ai,
        "extract_meal_menus",
        lambda *args: pytest.fail("Gemini must not run without a selected date."),
    )

    with TestClient(app) as client:
        response = post_image(
            client,
            selected_date=None,
            reference_date=None,
        )

    assert response.status_code == 422


def test_monthly_selected_date_must_match_reference_month(
    extraction_files: tuple[Path, Path],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        ai,
        "extract_meal_menus",
        lambda *args: pytest.fail("Gemini must not run for a mismatched month."),
    )

    with TestClient(app) as client:
        response = post_image(
            client,
            scope="monthly",
            selected_date="2026-11-24",
            reference_date=None,
            reference_month="2026-12",
        )

    assert response.status_code == 422


def test_daily_image_with_unmatched_date_requests_confirmation_without_candidates(
    extraction_files: tuple[Path, Path],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mock_extraction(
        monkeypatch,
        candidate(
            date_text="2026년 11월 25일",
            date_iso="2026-11-25",
            date_has_explicit_year=True,
        ),
    )

    with TestClient(app) as client:
        response = post_image(client, selected_date="2026-11-24")

    assert response.status_code == 200
    payload = response.json()
    assert payload["menus"] == []
    assert payload["selected_date"] == "2026-11-24"
    assert payload["extraction_warnings"]
    assert "급식 없음" in payload["extraction_warnings"][0]


def test_gemini_failure_keeps_existing_reviewed_data_unchanged(
    extraction_files: tuple[Path, Path],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    date_path, _ = extraction_files
    original = date_meal_sheet_storage.save_date_meal_sheet(
        "2026-11-24",
        "REVIEWED",
        [
            {
                "id": "existing",
                "name": "기존 메뉴",
                "allergens": ["우유"],
                "is_information_complete": True,
                "meal_type": None,
            }
        ],
        replace_existing=False,
    )
    before = date_path.read_bytes()

    def fail(
        image_bytes: bytes, mime_type: str, scope: str, selected_date: date
    ) -> GeminiMealExtraction:
        raise ai.GeminiServiceError("mock service failure")

    monkeypatch.setattr(ai, "extract_meal_menus", fail)

    with TestClient(app) as client:
        response = post_image(client)
        after = client.get("/api/meal-sheets/2026-11-24")

    assert response.status_code == 502
    assert "기존 저장 데이터는 변경되지 않았습니다" in response.json()["detail"]
    assert after.json()["menus"][0]["name"] == original["menus"][0]["name"]
    assert date_path.read_bytes() == before


def test_extracted_candidate_only_enters_comparison_after_reviewed_save(
    extraction_files: tuple[Path, Path],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    date_path, _ = extraction_files
    profile_storage.save_profile(["우유"])
    mock_extraction(
        monkeypatch,
        candidate(
            name="AI 후보",
            allergen_marking="(2)",
        ),
    )

    with TestClient(app) as client:
        extracted = post_image(client)
        assert extracted.status_code == 200
        candidate_menu = extracted.json()["menus"][0]
        assert not date_path.exists()

        before_review = client.get("/api/meal-sheets/2026-11-24")
        saved = client.put(
            "/api/meal-sheets/2026-11-24",
            json={
                "status": "REVIEWED",
                "menus": [
                    {
                        "id": candidate_menu["id"],
                        "name": "사용자가 확인한 메뉴",
                        "allergens": candidate_menu["allergens"],
                        "is_information_complete": True,
                        "meal_type": None,
                    }
                ],
            },
        )
        analysis = client.post("/api/meal-sheets/2026-11-24/analyze")

    assert before_review.json()["status"] == "NO_DATA"
    assert saved.status_code == 200
    assert saved.json()["status"] == "REVIEWED"
    assert analysis.status_code == 200
    assert analysis.json()["results"][0]["menu_name"] == "사용자가 확인한 메뉴"
    assert analysis.json()["results"][0]["status"] == "MATCH"


def test_ai_client_uses_model_environment_and_structured_schema(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output = GeminiMealExtraction(
        menus=[
            ExtractedMeal(
                date_text="2026-11-24",
                date_iso="2026-11-24",
                date_has_explicit_year=True,
                name="우유죽",
                allergen_marking="(2)",
            )
        ]
    ).model_dump_json()
    recorded: dict[str, object] = {}

    class FakeInteractions:
        def create(self, **kwargs: object) -> SimpleNamespace:
            recorded.update(kwargs)
            return SimpleNamespace(output_text=output)

    class FakeClient:
        interactions = FakeInteractions()

    monkeypatch.setenv("GEMINI_MODEL", "test-model")
    monkeypatch.setattr(ai, "create_gemini_client", lambda: FakeClient())

    result = ai.extract_meal_menus(
        b"image-bytes",
        "image/png",
        "monthly",
        date(2026, 11, 24),
    )

    assert result.menus[0].name == "우유죽"
    assert recorded["model"] == "test-model"
    assert recorded["response_format"]["mime_type"] == "application/json"
    inputs = recorded["input"]
    assert isinstance(inputs, list)
    image_part = inputs[1]
    assert image_part["mime_type"] == "image/png"
    assert base64.b64decode(image_part["data"]) == b"image-bytes"
    assert "2026-11-24" in inputs[0]["text"]
    assert "각 칸 머리의 일자·요일" in inputs[0]["text"]


def test_ai_client_reports_missing_model_without_calling_gemini(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("GEMINI_MODEL", raising=False)
    monkeypatch.setattr(
        ai,
        "create_gemini_client",
        lambda: pytest.fail("Gemini client should not be created."),
    )

    with pytest.raises(ai.GeminiConfigurationError, match="GEMINI_MODEL"):
        ai.extract_meal_menus(
            b"image-bytes",
            "image/png",
            "daily",
            date(2026, 11, 24),
        )


def test_ai_invalid_structured_response_is_a_service_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeInteractions:
        def create(self, **kwargs: object) -> SimpleNamespace:
            return SimpleNamespace(output_text=json.dumps({"unexpected": True}))

    class FakeClient:
        interactions = FakeInteractions()

    monkeypatch.setenv("GEMINI_MODEL", "test-model")
    monkeypatch.setattr(ai, "create_gemini_client", lambda: FakeClient())

    with pytest.raises(ai.GeminiServiceError, match="응답"):
        ai.extract_meal_menus(
            b"image-bytes",
            "image/png",
            "daily",
            date(2026, 11, 24),
        )
