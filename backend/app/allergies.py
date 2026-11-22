ALLERGY_OPTIONS: tuple[str, ...] = (
    "난류(가금류)",
    "우유",
    "메밀",
    "땅콩",
    "대두",
    "밀",
    "고등어",
    "게",
    "새우",
    "돼지고기",
    "복숭아",
    "토마토",
    "아황산류",
    "호두",
    "닭고기",
    "쇠고기",
    "오징어",
    "조개류(굴·전복·홍합 포함)",
    "잣",
)

ALLERGEN_NUMBER_TO_NAME: dict[int, str] = {
    1: "난류(가금류)",
    2: "우유",
    3: "메밀",
    4: "땅콩",
    5: "대두",
    6: "밀",
    7: "고등어",
    8: "게",
    9: "새우",
    10: "돼지고기",
    11: "복숭아",
    12: "토마토",
    13: "아황산류",
    14: "호두",
    15: "닭고기",
    16: "쇠고기",
    17: "오징어",
    18: "조개류(굴·전복·홍합 포함)",
    19: "잣",
}

ALLERGEN_NAME_ALIASES = {
    "달걀": "난류(가금류)",
    "난류(달걀 등 가금류 알)": "난류(가금류)",
}


def normalize_allergen_name(value: str) -> str | None:
    normalized = value.strip()
    if normalized in ALLERGY_OPTIONS:
        return normalized
    return ALLERGEN_NAME_ALIASES.get(normalized)
