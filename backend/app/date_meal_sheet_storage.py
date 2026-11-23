import json
import tempfile
from datetime import date
from pathlib import Path
from typing import Literal, TypedDict

from backend.app import meal_sheet_storage

MEAL_SHEETS_FILE = (
    Path(__file__).resolve().parents[1] / "data" / "meal_sheets.json"
)
LEGACY_MEAL_SHEET_FILE = meal_sheet_storage.MEAL_SHEET_FILE

MealSheetStatus = Literal["NO_DATA", "DRAFT", "REVIEWED", "NO_MEAL"]
StoredMealSheetStatus = Literal["DRAFT", "REVIEWED", "NO_MEAL"]
MealType = Literal["morning_snack", "lunch", "afternoon_snack"]
MEAL_TYPES = {"morning_snack", "lunch", "afternoon_snack"}


class DateMealMenu(TypedDict):
    id: str
    name: str
    allergens: list[str] | None
    is_information_complete: bool
    meal_type: MealType | None


class DateMealSheet(TypedDict):
    status: StoredMealSheetStatus
    source: Literal["manual"]
    service_status: Literal["provided", "no_meal"]
    reviewed: bool
    menus: list[DateMealMenu]


class DateMealSheetResponse(TypedDict):
    date: str
    status: MealSheetStatus
    source: Literal["manual"]
    service_status: Literal["provided", "no_meal"] | None
    reviewed: bool
    menus: list[DateMealMenu]


class UnassignedMealSheet(TypedDict):
    status: Literal["UNASSIGNED"]
    date: None
    source: Literal["manual"]
    reviewed: bool
    menus: list[meal_sheet_storage.MealMenu]


class DateMealSheetStorageError(Exception):
    pass


class ExistingDateMealSheetError(Exception):
    pass


class InvalidMonthError(DateMealSheetStorageError):
    pass


def _validate_date(value: str) -> str:
    try:
        parsed = date.fromisoformat(value)
    except ValueError as exc:
        raise DateMealSheetStorageError("급식 날짜 형식이 올바르지 않습니다.") from exc
    if parsed.isoformat() != value:
        raise DateMealSheetStorageError("급식 날짜 형식이 올바르지 않습니다.")
    return value


def _validate_menu(raw_menu: object) -> DateMealMenu:
    if not isinstance(raw_menu, dict):
        raise DateMealSheetStorageError("저장된 날짜별 급식표 형식이 올바르지 않습니다.")

    menu_id = raw_menu.get("id")
    name = raw_menu.get("name")
    allergens = raw_menu.get("allergens")
    information_complete = raw_menu.get("is_information_complete")
    meal_type = raw_menu.get("meal_type")
    if (
        not isinstance(menu_id, str)
        or not menu_id.strip()
        or not isinstance(name, str)
        or (
            allergens is not None
            and (
                not isinstance(allergens, list)
                or any(not isinstance(item, str) for item in allergens)
            )
        )
        or not isinstance(information_complete, bool)
        or (
            meal_type is not None
            and (
                not isinstance(meal_type, str)
                or meal_type not in MEAL_TYPES
            )
        )
    ):
        raise DateMealSheetStorageError("저장된 날짜별 급식표 형식이 올바르지 않습니다.")

    return {
        "id": menu_id,
        "name": name,
        "allergens": allergens,
        "is_information_complete": information_complete,
        "meal_type": meal_type,
    }


def _validate_record(raw_record: object) -> DateMealSheet:
    if not isinstance(raw_record, dict):
        raise DateMealSheetStorageError("저장된 날짜별 급식표 형식이 올바르지 않습니다.")

    status = raw_record.get("status")
    source = raw_record.get("source")
    service_status = raw_record.get("service_status")
    reviewed = raw_record.get("reviewed")
    raw_menus = raw_record.get("menus")
    if (
        not isinstance(status, str)
        or status not in {"DRAFT", "REVIEWED", "NO_MEAL"}
        or source != "manual"
        or not isinstance(service_status, str)
        or service_status not in {"provided", "no_meal"}
        or not isinstance(reviewed, bool)
        or not isinstance(raw_menus, list)
    ):
        raise DateMealSheetStorageError("저장된 날짜별 급식표 형식이 올바르지 않습니다.")

    menus = [_validate_menu(menu) for menu in raw_menus]
    menu_ids = [menu["id"] for menu in menus]
    if len(menu_ids) != len(set(menu_ids)):
        raise DateMealSheetStorageError("저장된 날짜별 급식표 형식이 올바르지 않습니다.")

    if status == "NO_MEAL":
        if service_status != "no_meal" or not reviewed or menus:
            raise DateMealSheetStorageError("저장된 날짜별 급식표 형식이 올바르지 않습니다.")
    elif (
        service_status != "provided"
        or reviewed != (status == "REVIEWED")
        or (reviewed and (not menus or any(not menu["name"].strip() for menu in menus)))
    ):
        raise DateMealSheetStorageError("저장된 날짜별 급식표 형식이 올바르지 않습니다.")

    return {
        "status": status,
        "source": "manual",
        "service_status": service_status,
        "reviewed": reviewed,
        "menus": menus,
    }


def _validate_legacy(raw_legacy: object) -> dict[str, object]:
    try:
        legacy = meal_sheet_storage._validate_meal_sheet(raw_legacy)
    except meal_sheet_storage.MealSheetStorageError as exc:
        raise DateMealSheetStorageError(
            "날짜가 없는 기존 급식표 형식을 확인할 수 없습니다. 기존 파일은 변경하지 않았습니다."
        ) from exc
    return {
        "source": legacy["source"],
        "reviewed": legacy["reviewed"],
        "menus": legacy["menus"],
    }


def _empty_store() -> dict[str, object]:
    return {"version": 1, "sheets": {}, "unassigned_legacy": None}


def _validate_store(value: object) -> dict[str, object]:
    if (
        not isinstance(value, dict)
        or type(value.get("version")) is not int
        or value.get("version") != 1
        or not isinstance(value.get("sheets"), dict)
        or "unassigned_legacy" not in value
    ):
        raise DateMealSheetStorageError("날짜별 급식표 저장 형식이 올바르지 않습니다.")

    sheets: dict[str, DateMealSheet] = {}
    for raw_date, raw_record in value["sheets"].items():
        if not isinstance(raw_date, str):
            raise DateMealSheetStorageError("날짜별 급식표 저장 형식이 올바르지 않습니다.")
        selected_date = _validate_date(raw_date)
        sheets[selected_date] = _validate_record(raw_record)

    legacy = value["unassigned_legacy"]
    if legacy is not None:
        legacy = _validate_legacy(legacy)

    return {
        "version": 1,
        "sheets": sheets,
        "unassigned_legacy": legacy,
    }


def _write_store(store: dict[str, object]) -> None:
    temporary_path: Path | None = None
    try:
        MEAL_SHEETS_FILE.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=MEAL_SHEETS_FILE.parent,
            prefix=".meal-sheets-",
            suffix=".tmp",
            delete=False,
        ) as file:
            temporary_path = Path(file.name)
            json.dump(store, file, ensure_ascii=False, indent=2)
            file.write("\n")
        temporary_path.replace(MEAL_SHEETS_FILE)
    except (OSError, UnicodeError) as exc:
        raise DateMealSheetStorageError(
            "날짜별 급식표 정보를 저장할 수 없습니다."
        ) from exc
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)


def _migrate_legacy_if_needed() -> dict[str, object]:
    store = _empty_store()
    if not LEGACY_MEAL_SHEET_FILE.exists():
        return store

    try:
        legacy = _validate_legacy(meal_sheet_storage.load_meal_sheet())
    except meal_sheet_storage.MealSheetStorageError as exc:
        raise DateMealSheetStorageError(
            "날짜가 없는 기존 급식표를 읽을 수 없습니다. 기존 파일은 변경하지 않았습니다."
        ) from exc

    store["unassigned_legacy"] = legacy
    _write_store(store)
    return store


def _load_store() -> dict[str, object]:
    try:
        with MEAL_SHEETS_FILE.open(encoding="utf-8") as file:
            value = json.load(file)
    except FileNotFoundError:
        return _migrate_legacy_if_needed()
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise DateMealSheetStorageError(
            "날짜별 급식표 정보를 읽을 수 없습니다."
        ) from exc

    return _validate_store(value)


def get_date_meal_sheet(selected_date: str) -> DateMealSheetResponse:
    selected_date = _validate_date(selected_date)
    store = _load_store()
    sheets = store["sheets"]
    record = sheets.get(selected_date)
    if record is None:
        return {
            "date": selected_date,
            "status": "NO_DATA",
            "source": "manual",
            "service_status": None,
            "reviewed": False,
            "menus": [],
        }
    return {"date": selected_date, **record}


def list_month_meal_sheets(month: str) -> list[DateMealSheetResponse]:
    try:
        year, month_number = (int(part) for part in month.split("-"))
        if len(month) != 7 or not 1 <= month_number <= 12:
            raise ValueError
        date(year, month_number, 1)
    except ValueError as exc:
        raise InvalidMonthError("월 형식이 올바르지 않습니다.") from exc

    store = _load_store()
    sheets = store["sheets"]
    return [
        {"date": selected_date, **sheets[selected_date]}
        for selected_date in sorted(sheets)
        if selected_date.startswith(month)
    ]


def get_unassigned_legacy_meal_sheet() -> dict[str, object]:
    store = _load_store()
    legacy = store["unassigned_legacy"]
    if legacy is None:
        return {
            "status": "NO_DATA",
            "date": None,
            "source": "manual",
            "reviewed": False,
            "menus": [],
        }
    return {
        "status": "UNASSIGNED",
        "date": None,
        **legacy,
    }


def save_date_meal_sheet(
    selected_date: str,
    status: StoredMealSheetStatus,
    menus: list[DateMealMenu],
    replace_existing: bool,
) -> DateMealSheetResponse:
    selected_date = _validate_date(selected_date)
    store = _load_store()
    sheets = store["sheets"]
    if selected_date in sheets and not replace_existing:
        raise ExistingDateMealSheetError(
            "해당 날짜에 저장된 급식표가 있습니다. 기존 데이터를 유지하거나 덮어쓰기를 확인해 주세요."
        )

    validated_menus = [_validate_menu(menu) for menu in menus]
    menu_ids = [menu["id"] for menu in validated_menus]
    if len(menu_ids) != len(set(menu_ids)):
        raise DateMealSheetStorageError("중복 메뉴 ID는 사용할 수 없습니다.")
    if status == "NO_MEAL":
        if validated_menus:
            raise DateMealSheetStorageError("급식 없음 상태에는 메뉴를 저장할 수 없습니다.")
        service_status: Literal["provided", "no_meal"] = "no_meal"
        reviewed = True
    else:
        if status == "REVIEWED" and (
            not validated_menus
            or any(not menu["name"].strip() for menu in validated_menus)
        ):
            raise DateMealSheetStorageError(
                "검토 완료로 저장하려면 메뉴명이 있는 메뉴를 하나 이상 추가해 주세요."
            )
        service_status = "provided"
        reviewed = status == "REVIEWED"

    record = _validate_record(
        {
            "status": status,
            "source": "manual",
            "service_status": service_status,
            "reviewed": reviewed,
            "menus": validated_menus,
        }
    )
    sheets[selected_date] = record
    _write_store(store)
    return {"date": selected_date, **record}
