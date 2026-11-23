import re
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal, TypedDict

from backend.app.allergies import (
    ALLERGEN_NUMBER_TO_NAME,
    normalize_allergen_name,
)

ComparisonStatus = Literal["MATCH", "CHECK_NEEDED", "NOT_IDENTIFIED"]

NUMBERED_ALLERGEN_PATTERN = re.compile(
    r"(?P<number>[1-9]|1[0-9])(?:\.\s*(?P<name>.+))?"
)
LEGACY_LEGEND_PREFIX = "범례 확인 필요:"
CIRCLED_MARKING_PATTERN = re.compile(r"[\u2460-\u2472]+")


@dataclass(frozen=True)
class MenuItem:
    id: str
    name: str
    allergens: tuple[str, ...] | None
    is_information_complete: bool


class ComparisonResult(TypedDict):
    menu_id: str
    menu_name: str
    status: ComparisonStatus
    matched_allergens: list[str]
    evidence: list[str]
    reason: str


def _resolve_allergen(label: str) -> str | None:
    normalized = label.strip()
    canonical_name = normalize_allergen_name(normalized)
    if canonical_name:
        return canonical_name

    match = NUMBERED_ALLERGEN_PATTERN.fullmatch(normalized)
    if match is None:
        return None

    allergen = ALLERGEN_NUMBER_TO_NAME.get(int(match.group("number")))
    if allergen is None:
        return None
    provided_name = match.group("name")
    if provided_name is not None:
        normalized_name = provided_name.strip()
        if normalize_allergen_name(normalized_name) != allergen:
            return None
    return allergen


def _resolve_clear_circled_marking(label: str) -> set[str] | None:
    marking = label.strip().removeprefix(LEGACY_LEGEND_PREFIX).strip()
    if not CIRCLED_MARKING_PATTERN.fullmatch(marking):
        return None
    return {
        ALLERGEN_NUMBER_TO_NAME[ord(character) - 0x2460 + 1]
        for character in marking
    }


def compare_menus(
    profile_allergies: Sequence[str], menus: Sequence[MenuItem]
) -> list[ComparisonResult]:
    registered = list(dict.fromkeys(profile_allergies))
    results: list[ComparisonResult] = []

    for menu in menus:
        evidence = list(dict.fromkeys(menu.allergens or ()))
        resolved: set[str] = set()
        unrecognized: list[str] = []
        has_clear_circled_marking = False
        for label in evidence:
            if (allergen := _resolve_allergen(label)) is not None:
                resolved.add(allergen)
            elif (circled := _resolve_clear_circled_marking(label)) is not None:
                resolved.update(circled)
                has_clear_circled_marking = True
            else:
                unrecognized.append(label)
        matched = [allergen for allergen in registered if allergen in resolved]

        concerns: list[str] = []
        if not menu.name.strip():
            concerns.append("메뉴명이 입력되지 않았습니다.")
        if menu.allergens is None:
            concerns.append("알레르기 표시 정보가 없습니다.")
        if not menu.is_information_complete and not (
            has_clear_circled_marking and not unrecognized
        ):
            concerns.append("표시 정보를 충분히 확인하지 못했습니다.")
        if unrecognized:
            concerns.append("알레르기 표시 중 해석하지 못한 부분이 있습니다.")

        if matched:
            status: ComparisonStatus = "MATCH"
            reason = (
                "급식표에 표시된 항목 중 등록 알레르기 "
                f"{', '.join(matched)}와 일치하는 표시가 있습니다."
            )
            if concerns:
                reason += " 추가 확인 사항: " + " ".join(concerns)
            else:
                reason += " 실제 원재료와 조리 과정은 담당자에게 확인해 주세요."
        elif concerns:
            status = "CHECK_NEEDED"
            reason = "추가 확인이 필요합니다. " + " ".join(concerns)
        else:
            status = "NOT_IDENTIFIED"
            reason = (
                "현재 확인된 표시에서 등록 항목과 일치하는 알레르기를 찾지 "
                "못했습니다. 이는 섭취 안전을 보장하지 않습니다."
            )

        results.append(
            {
                "menu_id": menu.id,
                "menu_name": menu.name,
                "status": status,
                "matched_allergens": matched,
                "evidence": evidence,
                "reason": reason,
            }
        )

    return results
