import re
from datetime import date
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field

from backend.app.allergies import (
    ALLERGEN_NUMBER_TO_NAME,
    normalize_allergen_name,
)

MealType = Literal["morning_snack", "lunch", "afternoon_snack"]
ExtractionScope = Literal["daily", "monthly"]
LegendStatus = Literal["NO_LEGEND", "VERIFIED", "NEEDS_CONFIRMATION"]


class ExtractedMeal(BaseModel):
    date_text: str | None = Field(
        default=None,
        max_length=80,
        description="급식표에 표시된 날짜 문자열 그대로. 확인할 수 없으면 null.",
    )
    date_iso: str | None = Field(
        default=None,
        max_length=10,
        description="4자리 연도가 이미지에 명시된 경우만 YYYY-MM-DD. 아니면 null.",
    )
    date_has_explicit_year: bool = Field(
        default=False,
        description="4자리 연도가 이미지에 실제로 인쇄되어 있는지 여부.",
    )
    meal_type: MealType | None = Field(
        default=None,
        description="명확한 식사 구분 제목이 있는 경우만 설정. 불명확하면 null.",
    )
    name: str = Field(
        default="",
        max_length=160,
        description="이미지에서 읽히는 메뉴명. 읽을 수 없으면 빈 문자열.",
    )
    allergen_marking: str | None = Field(
        default=None,
        max_length=160,
        description="해당 메뉴에 인쇄된 알레르기 숫자/기호를 그대로 기록.",
    )


class ExtractedLegendEntry(BaseModel):
    number: int | None = Field(
        default=None,
        description="범례에 표시된 알레르기 번호. 읽을 수 없으면 null.",
    )
    label: str = Field(
        default="",
        max_length=120,
        description="해당 번호에 연결된 범례 항목명을 그대로 기록.",
    )


class GeminiMealExtraction(BaseModel):
    menus: list[ExtractedMeal] = Field(
        max_length=200,
        description="이미지에 실제로 표시된 메뉴별 후보 목록.",
    )
    legend_present: bool = Field(
        default=False,
        description="이미지에 알레르기 번호 범례가 실제로 있는지 여부.",
    )
    legend_readable: bool = Field(
        default=True,
        description="이미지에 있는 범례를 읽을 수 있는지 여부.",
    )
    legend_entries: list[ExtractedLegendEntry] = Field(
        default_factory=list,
        max_length=19,
        description="이미지 범례에서 읽힌 번호와 항목명.",
    )


class ImageMenuCandidate(BaseModel):
    id: str
    date: date | None
    date_text: str | None
    date_requires_confirmation: bool
    name: str
    meal_type: MealType | None
    allergen_marking: str | None
    allergen_numbers: list[int]
    allergens: list[str] | None
    warnings: list[str]
    is_information_complete: Literal[False] = False


class MealImageExtractionResponse(BaseModel):
    source: Literal["uploaded-image"] = "uploaded-image"
    reviewed: Literal[False] = False
    scope: ExtractionScope
    selected_date: date
    reference_date: date | None
    reference_month: str | None
    legend_status: LegendStatus
    legend_warnings: list[str]
    extraction_warnings: list[str]
    menus: list[ImageMenuCandidate]


_CIRCLED_NUMBER_TO_INT = {
    chr(0x2460 + number - 1): number
    for number in range(1, 20)
}
_NUMERIC_MARKING = re.compile(r"\d{1,2}(?:\s*(?:[.,]\s*|\s+)\d{1,2})*")
_MARKING_SEPARATORS = re.compile(r"[,，;；/|]+")


def _validate_full_date(menu: ExtractedMeal) -> tuple[date | None, bool]:
    if not menu.date_has_explicit_year or not menu.date_iso:
        return None, True
    try:
        parsed = date.fromisoformat(menu.date_iso)
    except ValueError:
        return None, True
    if parsed.isoformat() != menu.date_iso:
        return None, True
    return parsed, False


def _parse_image_month_day(date_text: str | None) -> tuple[int, int] | None:
    if not date_text or re.search(r"(?<!\d)\d{4}(?!\d)", date_text):
        return None

    patterns = (
        re.compile(
            r"(?<!\d)(?P<month>0?[1-9]|1[0-2])\s*월\s*"
            r"(?P<day>0?[1-9]|[12]\d|3[01])\s*일?(?!\d)"
        ),
        re.compile(
            r"(?<!\d)(?P<month>0?[1-9]|1[0-2])\s*[./-]\s*"
            r"(?P<day>0?[1-9]|[12]\d|3[01])(?![\d./-])"
        ),
    )
    matches = [
        match
        for pattern in patterns
        for match in pattern.finditer(date_text)
    ]
    if len(matches) != 1:
        return None

    month = int(matches[0].group("month"))
    day = int(matches[0].group("day"))
    try:
        date(2000, month, day)
    except ValueError:
        return None
    return month, day


def _parse_image_full_date(date_text: str | None) -> date | None:
    if not date_text:
        return None

    patterns = (
        re.compile(
            r"(?<!\d)(?P<year>\d{4})\s*년\s*"
            r"(?P<month>0?[1-9]|1[0-2])\s*월\s*"
            r"(?P<day>0?[1-9]|[12]\d|3[01])\s*일?(?!\d)"
        ),
        re.compile(
            r"(?<!\d)(?P<year>\d{4})\s*[./-]\s*"
            r"(?P<month>0?[1-9]|1[0-2])\s*[./-]\s*"
            r"(?P<day>0?[1-9]|[12]\d|3[01])(?![\d./-])"
        ),
        re.compile(
            r"(?<!\d)(?P<year>\d{4})\s*년\s*"
            r"(?P<month>0?[1-9]|1[0-2])\s*월"
            r"\s*[^\d\s][^\d]{0,39}(?P<day>0?[1-9]|[12]\d|3[01])\s*"
            r"(?:일|\([월화수목금토일]\))(?!\d)"
        ),
    )
    matches = [
        match
        for pattern in patterns
        for match in pattern.finditer(date_text)
    ]
    if len(matches) != 1:
        return None

    try:
        return date(
            int(matches[0].group("year")),
            int(matches[0].group("month")),
            int(matches[0].group("day")),
        )
    except ValueError:
        return None


def _matches_selected_date(menu: ExtractedMeal, selected_date: date) -> bool:
    candidate_date, _ = _validate_full_date(menu)
    if candidate_date is not None:
        printed_date = _parse_image_full_date(menu.date_text)
        if printed_date is None and menu.date_text:
            day_only = re.fullmatch(
                r"\s*(0?[1-9]|[12]\d|3[01])\s*(?:일|\([월화수목금토일]\))?\s*",
                menu.date_text,
            )
            if day_only and int(day_only.group(1)) == candidate_date.day:
                printed_date = candidate_date
        return (
            printed_date == candidate_date
            and candidate_date == selected_date
        )
    return _parse_image_month_day(menu.date_text) == (
        selected_date.month,
        selected_date.day,
    )


def _check_legend(
    extraction: GeminiMealExtraction,
) -> tuple[LegendStatus, set[int], list[str]]:
    if not extraction.legend_present and not extraction.legend_entries:
        return "NO_LEGEND", set(), []

    warnings: list[str] = []
    verified_numbers: set[int] = set()
    if not extraction.legend_present:
        warnings.append("범례 인식 결과가 일치하지 않아 번호 대응을 확인해야 합니다.")
    elif not extraction.legend_readable or not extraction.legend_entries:
        warnings.append("이미지의 알레르기 범례를 읽을 수 없어 번호 대응 확인이 필요합니다.")
    else:
        seen_numbers: set[int] = set()
        for entry in extraction.legend_entries:
            number = entry.number
            expected = ALLERGEN_NUMBER_TO_NAME.get(number) if number else None
            normalized_label = normalize_allergen_name(entry.label)
            if (
                number is None
                or expected is None
                or normalized_label != expected
                or number in seen_numbers
            ):
                warnings.append(
                    "이미지 범례가 알레르기 번호 대응표와 다르거나 불명확합니다."
                )
                continue
            seen_numbers.add(number)
            verified_numbers.add(number)

        if not verified_numbers and not warnings:
            warnings.append("이미지의 알레르기 범례에서 확인된 항목이 없습니다.")

    if warnings:
        return "NEEDS_CONFIRMATION", verified_numbers, list(dict.fromkeys(warnings))
    return "VERIFIED", verified_numbers, []


def _parse_allergen_marking(
    marking: str | None,
) -> tuple[list[int], list[str], list[str]]:
    if not marking or not marking.strip():
        return [], [], []

    normalized = marking.strip()
    direct_name = normalize_allergen_name(normalized)
    if direct_name:
        return [], [direct_name], []

    numbers: list[int] = []
    names: list[str] = []
    unknown: list[str] = []

    for raw_part in _MARKING_SEPARATORS.split(normalized):
        part = raw_part.strip()
        if not part:
            continue

        circled = [
            _CIRCLED_NUMBER_TO_INT[character]
            for character in part
            if character in _CIRCLED_NUMBER_TO_INT
        ]
        if circled:
            remainder = "".join(
                character
                for character in part
                if character not in _CIRCLED_NUMBER_TO_INT
            ).strip()
            numbers.extend(circled)
            if remainder:
                unknown.append(remainder)
            continue

        numeric_part = part.strip("()（）[]［］{} ")
        if _NUMERIC_MARKING.fullmatch(numeric_part):
            numbers.extend(
                int(value)
                for value in re.findall(r"\d{1,2}", numeric_part)
            )
            continue

        normalized_name = normalize_allergen_name(numeric_part)
        if normalized_name:
            names.append(normalized_name)
        else:
            unknown.append(part)

    return (
        list(dict.fromkeys(numbers)),
        list(dict.fromkeys(names)),
        list(dict.fromkeys(unknown)),
    )


def build_image_extraction_response(
    extraction: GeminiMealExtraction,
    scope: ExtractionScope,
    selected_date: date,
    reference_date: date | None,
    reference_month: str | None,
) -> MealImageExtractionResponse:
    legend_status, verified_legend_numbers, legend_warnings = _check_legend(
        extraction
    )
    has_legend = extraction.legend_present or bool(extraction.legend_entries)
    candidates: list[ImageMenuCandidate] = []
    matching_menus = [
        menu
        for menu in extraction.menus
        if _matches_selected_date(menu, selected_date)
        or (scope == "daily" and not menu.date_text and not menu.date_iso)
    ]
    extraction_warnings: list[str] = []

    if not matching_menus:
        if extraction.menus:
            extraction_warnings.append(
                f"선택한 날짜 {selected_date.isoformat()}에 연결된 메뉴를 확인하지 못했습니다. "
                "급식 없음으로 확정하지 말고 이미지 날짜를 확인하거나 메뉴를 직접 입력해 주세요."
            )
        else:
            extraction_warnings.append(
                "이미지에서 메뉴를 확인하지 못했습니다. 급식 없음으로 간주하지 말고 "
                "이미지와 날짜를 확인하거나 메뉴를 직접 입력해 주세요."
            )
    elif len(matching_menus) < len(extraction.menus):
        extraction_warnings.append(
            f"선택한 날짜 {selected_date.isoformat()}에 명확히 연결된 메뉴만 표시했습니다. "
            "다른 날짜 또는 날짜를 확인할 수 없는 메뉴는 제외했습니다."
        )
    if any(
        _validate_full_date(menu)[0] is None for menu in matching_menus
    ):
        extraction_warnings.append(
            "이미지 날짜에 연도가 없거나 확인되지 않았습니다. 선택한 날짜와 실제 이미지 날짜를 "
            "구분해 확인하고 저장 날짜를 직접 지정해 주세요."
        )

    for menu in matching_menus:
        candidate_date, date_requires_confirmation = _validate_full_date(menu)
        numbers, names, unknown = _parse_allergen_marking(
            menu.allergen_marking
        )
        warnings: list[str] = []

        if date_requires_confirmation:
            warnings.append(
                "연도까지 확인된 날짜가 아닙니다. 저장 전에 날짜를 직접 지정해 주세요."
            )
        if not menu.name.strip():
            warnings.append("메뉴명을 읽지 못했습니다. 메뉴명을 직접 확인해 주세요.")

        allergens: list[str] | None = None
        if menu.allergen_marking and menu.allergen_marking.strip():
            unresolved: list[str] = []
            if legend_status == "NEEDS_CONFIRMATION":
                unresolved.append(menu.allergen_marking.strip())
            else:
                names.extend(
                    name
                    for number in numbers
                    if (name := ALLERGEN_NUMBER_TO_NAME.get(number))
                    and (not has_legend or number in verified_legend_numbers)
                )
                unresolved.extend(
                    f"번호 {number} 확인 필요"
                    for number in numbers
                    if number not in ALLERGEN_NUMBER_TO_NAME
                    or (has_legend and number not in verified_legend_numbers)
                )
                unresolved.extend(unknown)
            allergens = list(dict.fromkeys([*names, *unresolved])) or [
                menu.allergen_marking.strip()
            ]
            if unresolved:
                warnings.append(
                    "알레르기 표시 일부를 대응표로 해석할 수 없어 직접 확인해야 합니다."
                )
        else:
            warnings.append(
                "알레르기 표시를 확인하지 못했습니다. 표시가 없다고 단정하지 말고 직접 확인해 주세요."
            )

        if legend_warnings and numbers:
            warnings.extend(legend_warnings)

        candidates.append(
            ImageMenuCandidate(
                id=f"extract-{uuid4().hex}",
                date=candidate_date,
                date_text=menu.date_text,
                date_requires_confirmation=date_requires_confirmation,
                name=menu.name.strip(),
                meal_type=menu.meal_type,
                allergen_marking=menu.allergen_marking,
                allergen_numbers=numbers,
                allergens=allergens,
                warnings=list(dict.fromkeys(warnings)),
            )
        )

    return MealImageExtractionResponse(
        scope=scope,
        selected_date=selected_date,
        reference_date=reference_date,
        reference_month=reference_month,
        legend_status=legend_status,
        legend_warnings=legend_warnings,
        extraction_warnings=extraction_warnings,
        menus=candidates,
    )
