from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal, TypedDict

from backend.app.allergies import ALLERGY_OPTIONS

ComparisonStatus = Literal["MATCH", "CHECK_NEEDED", "NOT_IDENTIFIED"]

ALLERGEN_ALIASES = {"달걀": "난류(가금류)"}


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
    if normalized in ALLERGY_OPTIONS:
        return normalized
    return ALLERGEN_ALIASES.get(normalized)


def compare_menus(
    profile_allergies: Sequence[str], menus: Sequence[MenuItem]
) -> list[ComparisonResult]:
    registered = list(dict.fromkeys(profile_allergies))
    results: list[ComparisonResult] = []

    for menu in menus:
        evidence = list(dict.fromkeys(menu.allergens or ()))
        resolved = {
            allergen
            for label in evidence
            if (allergen := _resolve_allergen(label)) is not None
        }
        unrecognized = [
            label for label in evidence if _resolve_allergen(label) is None
        ]
        matched = [allergen for allergen in registered if allergen in resolved]

        concerns: list[str] = []
        if not menu.name.strip():
            concerns.append("메뉴명이 입력되지 않았습니다.")
        if menu.allergens is None:
            concerns.append("알레르기 표시 정보가 없습니다.")
        if not menu.is_information_complete:
            concerns.append("표시 정보를 충분히 확인하지 못했습니다.")
        if unrecognized:
            concerns.append(
                f"해석할 수 없는 표시({', '.join(unrecognized)})가 있습니다."
            )

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
