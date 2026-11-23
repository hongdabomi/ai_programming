import json
import tempfile
from pathlib import Path
from typing import TypedDict

MEAL_SHEET_FILE = (
    Path(__file__).resolve().parents[1] / "data" / "meal_sheet.json"
)


class MealMenu(TypedDict):
    id: str
    name: str
    allergens: list[str] | None
    is_information_complete: bool


class MealSheet(TypedDict):
    source: str
    reviewed: bool
    menus: list[MealMenu]


class MealSheetStorageError(Exception):
    pass


def _validate_meal_sheet(value: object) -> MealSheet:
    if not isinstance(value, dict):
        raise MealSheetStorageError("저장된 급식표 정보 형식이 올바르지 않습니다.")

    source = value.get("source")
    reviewed = value.get("reviewed")
    raw_menus = value.get("menus")
    if (
        source != "manual"
        or not isinstance(reviewed, bool)
        or not isinstance(raw_menus, list)
    ):
        raise MealSheetStorageError("저장된 급식표 정보 형식이 올바르지 않습니다.")

    menus: list[MealMenu] = []
    seen_ids: set[str] = set()
    for raw_menu in raw_menus:
        if not isinstance(raw_menu, dict):
            raise MealSheetStorageError(
                "저장된 급식표 정보 형식이 올바르지 않습니다."
            )

        menu_id = raw_menu.get("id")
        name = raw_menu.get("name")
        allergens = raw_menu.get("allergens")
        is_information_complete = raw_menu.get("is_information_complete")
        if (
            not isinstance(menu_id, str)
            or not menu_id.strip()
            or menu_id in seen_ids
            or not isinstance(name, str)
            or (
                allergens is not None
                and (
                    not isinstance(allergens, list)
                    or any(not isinstance(item, str) for item in allergens)
                )
            )
            or not isinstance(is_information_complete, bool)
        ):
            raise MealSheetStorageError(
                "저장된 급식표 정보 형식이 올바르지 않습니다."
            )

        if reviewed and not name.strip():
            raise MealSheetStorageError(
                "검토 완료된 급식 메뉴에는 메뉴명이 필요합니다."
            )

        seen_ids.add(menu_id)
        menus.append(
            {
                "id": menu_id,
                "name": name,
                "allergens": allergens,
                "is_information_complete": is_information_complete,
            }
        )

    if reviewed and not menus:
        raise MealSheetStorageError(
            "메뉴를 추가한 뒤 검토 완료로 저장해 주세요."
        )

    return {"source": "manual", "reviewed": reviewed, "menus": menus}


def load_meal_sheet() -> MealSheet:
    try:
        with MEAL_SHEET_FILE.open(encoding="utf-8") as file:
            data = json.load(file)
    except FileNotFoundError:
        return {"source": "manual", "reviewed": False, "menus": []}
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise MealSheetStorageError(
            "저장된 급식표 정보를 읽을 수 없습니다."
        ) from exc

    return _validate_meal_sheet(data)


def save_meal_sheet(menus: list[MealMenu], reviewed: bool) -> MealSheet:
    meal_sheet = _validate_meal_sheet(
        {"source": "manual", "reviewed": reviewed, "menus": menus}
    )
    temporary_path: Path | None = None
    try:
        MEAL_SHEET_FILE.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=MEAL_SHEET_FILE.parent,
            prefix=".meal-sheet-",
            suffix=".tmp",
            delete=False,
        ) as file:
            temporary_path = Path(file.name)
            json.dump(meal_sheet, file, ensure_ascii=False, indent=2)
            file.write("\n")
        temporary_path.replace(MEAL_SHEET_FILE)
    except (OSError, UnicodeError) as exc:
        raise MealSheetStorageError(
            "급식표 정보를 저장할 수 없습니다."
        ) from exc
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)

    return meal_sheet
