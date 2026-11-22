import re
from io import BytesIO
from datetime import date
from pathlib import Path
from typing import Literal

from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image, UnidentifiedImageError
from pydantic import BaseModel, Field, field_validator, model_validator

from backend.app.allergies import ALLERGEN_NUMBER_TO_NAME, ALLERGY_OPTIONS
from backend.app import ai, date_meal_sheet_storage, meal_sheet_storage, profile_storage
from backend.app.comparison import MenuItem, compare_menus
from backend.app.meal_image_extraction import (
    ExtractionScope,
    GeminiMealExtraction,
    MealImageExtractionResponse,
    build_image_extraction_response,
)

load_dotenv(Path(__file__).resolve().parents[2] / ".env")

app = FastAPI(title="한끼살핌 API")

MAX_IMAGE_BYTES = 10 * 1024 * 1024
MAX_IMAGE_PIXELS = 40_000_000
IMAGE_MIME_TYPES = {
    ".jpg": ("image/jpeg", {"image/jpeg", "image/jpg"}),
    ".jpeg": ("image/jpeg", {"image/jpeg", "image/jpg"}),
    ".png": ("image/png", {"image/png"}),
}

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5500",
        "http://localhost:5500",
    ],
    allow_methods=["GET", "POST", "PUT"],
    allow_headers=["Content-Type"],
)


class AllergySelection(BaseModel):
    allergies: list[str] = Field(max_length=len(ALLERGY_OPTIONS))

    @field_validator("allergies")
    @classmethod
    def validate_allergies(cls, allergies: list[str]) -> list[str]:
        if len(allergies) != len(set(allergies)):
            raise ValueError("중복 알레르기 항목은 선택할 수 없습니다.")
        if any(allergy not in ALLERGY_OPTIONS for allergy in allergies):
            raise ValueError("지원하지 않는 알레르기 항목이 포함되어 있습니다.")
        return allergies


class ProfileResponse(BaseModel):
    id: str
    allergies: list[str]


class MenuInput(BaseModel):
    id: str = Field(min_length=1, max_length=80)
    name: str = Field(default="", max_length=160)
    allergens: list[str] | None = None
    is_information_complete: bool = False

    @field_validator("name")
    @classmethod
    def normalize_name(cls, name: str) -> str:
        return name.strip()

    @field_validator("allergens")
    @classmethod
    def normalize_allergens(cls, allergens: list[str] | None) -> list[str] | None:
        if allergens is None:
            return None
        return [
            normalized
            for allergen in allergens
            if (normalized := allergen.strip())
        ]


class MealSheetUpdate(BaseModel):
    reviewed: bool = False
    menus: list[MenuInput]

    @model_validator(mode="after")
    def validate_meal_sheet(self) -> "MealSheetUpdate":
        menu_ids = [menu.id for menu in self.menus]
        if len(menu_ids) != len(set(menu_ids)):
            raise ValueError("중복 메뉴 ID는 사용할 수 없습니다.")
        if self.reviewed:
            if not self.menus:
                raise ValueError("메뉴를 추가한 뒤 검토 완료로 저장해 주세요.")
            if any(not menu.name for menu in self.menus):
                raise ValueError("검토 완료된 메뉴에는 메뉴명이 필요합니다.")
        return self


class ComparisonResultResponse(BaseModel):
    menu_id: str
    menu_name: str
    status: Literal["MATCH", "CHECK_NEEDED", "NOT_IDENTIFIED"]
    matched_allergens: list[str]
    evidence: list[str]
    reason: str


class AnalysisResponse(BaseModel):
    results: list[ComparisonResultResponse]
    disclaimer: str


class DateAnalysisResponse(BaseModel):
    date: date
    results: list[ComparisonResultResponse]
    disclaimer: str


class MealSheetResponse(BaseModel):
    source: Literal["manual"]
    reviewed: bool
    menus: list[MenuInput]


class DateMealMenuInput(MenuInput):
    meal_type: Literal["morning_snack", "lunch", "afternoon_snack"] | None = None


class DateMealSheetUpdate(BaseModel):
    status: Literal["DRAFT", "REVIEWED", "NO_MEAL"]
    menus: list[DateMealMenuInput]
    replace_existing: bool = False

    @model_validator(mode="after")
    def validate_date_meal_sheet(self) -> "DateMealSheetUpdate":
        menu_ids = [menu.id for menu in self.menus]
        if len(menu_ids) != len(set(menu_ids)):
            raise ValueError("중복 메뉴 ID는 사용할 수 없습니다.")
        if self.status == "NO_MEAL" and self.menus:
            raise ValueError("급식 없음 상태에는 메뉴를 저장할 수 없습니다.")
        if self.status == "REVIEWED":
            if not self.menus:
                raise ValueError(
                    "검토 완료로 저장하려면 메뉴를 하나 이상 추가해 주세요."
                )
            if any(not menu.name for menu in self.menus):
                raise ValueError("검토 완료된 메뉴에는 메뉴명이 필요합니다.")
        return self


class DateMealSheetResponse(BaseModel):
    date: date
    status: Literal["NO_DATA", "DRAFT", "REVIEWED", "NO_MEAL"]
    source: Literal["manual"]
    service_status: Literal["provided", "no_meal"] | None
    reviewed: bool
    menus: list[DateMealMenuInput]


class MonthMealSheetsResponse(BaseModel):
    month: str
    sheets: list[DateMealSheetResponse]


class UnassignedMealSheetResponse(BaseModel):
    status: Literal["NO_DATA", "UNASSIGNED"]
    date: None
    source: Literal["manual"]
    reviewed: bool
    menus: list[DateMealMenuInput]


def _validate_meal_image(
    image: UploadFile | None,
) -> tuple[bytes, str]:
    if image is None or not image.filename:
        raise HTTPException(
            status_code=400,
            detail="급식표 이미지 파일을 선택해 주세요.",
        )

    image_type = IMAGE_MIME_TYPES.get(Path(image.filename).suffix.lower())
    if image_type is None or image.content_type not in image_type[1]:
        raise HTTPException(
            status_code=415,
            detail="JPG, JPEG, PNG 형식의 이미지만 업로드할 수 있습니다.",
        )

    try:
        image_bytes = image.file.read(MAX_IMAGE_BYTES + 1)
    except OSError as exc:
        raise HTTPException(
            status_code=400,
            detail="업로드한 이미지 파일을 읽을 수 없습니다.",
        ) from exc

    if not image_bytes:
        raise HTTPException(
            status_code=400,
            detail="빈 이미지 파일은 처리할 수 없습니다.",
        )
    if len(image_bytes) > MAX_IMAGE_BYTES:
        raise HTTPException(
            status_code=413,
            detail="이미지 파일은 10MB 이하로 업로드해 주세요.",
        )

    expected_format = {
        "image/jpeg": "JPEG",
        "image/png": "PNG",
    }[image_type[0]]
    try:
        with Image.open(BytesIO(image_bytes)) as decoded_image:
            if decoded_image.format != expected_format:
                raise HTTPException(
                    status_code=415,
                    detail="파일 확장자와 실제 이미지 형식이 일치하지 않습니다.",
                )
            if decoded_image.width * decoded_image.height > MAX_IMAGE_PIXELS:
                raise HTTPException(
                    status_code=413,
                    detail="이미지 해상도가 너무 큽니다.",
                )
            decoded_image.verify()
    except HTTPException:
        raise
    except (
        Image.DecompressionBombError,
        OSError,
        UnidentifiedImageError,
    ) as exc:
        raise HTTPException(
            status_code=400,
            detail="유효한 JPG, JPEG, PNG 이미지를 업로드해 주세요.",
        ) from exc

    return image_bytes, image_type[0]


def _validate_reference_month(reference_month: str | None) -> str | None:
    if reference_month is None:
        return None
    if not re.fullmatch(r"\d{4}-(0[1-9]|1[0-2])", reference_month):
        raise HTTPException(status_code=422, detail="월 형식이 올바르지 않습니다.")
    try:
        date.fromisoformat(f"{reference_month}-01")
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail="월 형식이 올바르지 않습니다.",
        ) from exc
    return reference_month


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/allergens")
def get_allergen_options() -> dict[str, object]:
    return {
        "items": ALLERGY_OPTIONS,
        "numbered_items": [
            {"number": number, "name": name}
            for number, name in ALLERGEN_NUMBER_TO_NAME.items()
        ],
    }


@app.get("/api/profile", response_model=ProfileResponse)
def get_profile() -> ProfileResponse:
    try:
        return profile_storage.load_profile()
    except profile_storage.ProfileStorageError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.put("/api/profile", response_model=ProfileResponse)
def update_profile(selection: AllergySelection) -> ProfileResponse:
    try:
        return profile_storage.save_profile(selection.allergies)
    except profile_storage.ProfileStorageError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get(
    "/api/meal-sheets/current",
    response_model=MealSheetResponse,
)
def get_current_meal_sheet() -> MealSheetResponse:
    try:
        return meal_sheet_storage.load_meal_sheet()
    except meal_sheet_storage.MealSheetStorageError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.put(
    "/api/meal-sheets/current",
    response_model=MealSheetResponse,
)
def update_current_meal_sheet(
    update: MealSheetUpdate,
) -> MealSheetResponse:
    menus = [
        {
            "id": menu.id,
            "name": menu.name,
            "allergens": menu.allergens,
            "is_information_complete": menu.is_information_complete,
        }
        for menu in update.menus
    ]
    try:
        return meal_sheet_storage.save_meal_sheet(menus, update.reviewed)
    except meal_sheet_storage.MealSheetStorageError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get(
    "/api/meal-sheets",
    response_model=MonthMealSheetsResponse,
)
def get_month_meal_sheets(
    month: str = Query(pattern=r"^\d{4}-(0[1-9]|1[0-2])$"),
) -> MonthMealSheetsResponse:
    try:
        sheets = date_meal_sheet_storage.list_month_meal_sheets(month)
    except date_meal_sheet_storage.InvalidMonthError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except date_meal_sheet_storage.DateMealSheetStorageError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return MonthMealSheetsResponse(month=month, sheets=sheets)


@app.get(
    "/api/meal-sheets/unassigned",
    response_model=UnassignedMealSheetResponse,
)
def get_unassigned_meal_sheet() -> UnassignedMealSheetResponse:
    try:
        return date_meal_sheet_storage.get_unassigned_legacy_meal_sheet()
    except date_meal_sheet_storage.DateMealSheetStorageError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get(
    "/api/meal-sheets/{selected_date}",
    response_model=DateMealSheetResponse,
)
def get_date_meal_sheet(selected_date: date) -> DateMealSheetResponse:
    try:
        return date_meal_sheet_storage.get_date_meal_sheet(
            selected_date.isoformat()
        )
    except date_meal_sheet_storage.DateMealSheetStorageError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.put(
    "/api/meal-sheets/{selected_date}",
    response_model=DateMealSheetResponse,
)
def update_date_meal_sheet(
    selected_date: date,
    update: DateMealSheetUpdate,
) -> DateMealSheetResponse:
    menus = [
        {
            "id": menu.id,
            "name": menu.name,
            "allergens": menu.allergens,
            "is_information_complete": menu.is_information_complete,
            "meal_type": menu.meal_type,
        }
        for menu in update.menus
    ]
    try:
        return date_meal_sheet_storage.save_date_meal_sheet(
            selected_date.isoformat(),
            update.status,
            menus,
            update.replace_existing,
        )
    except date_meal_sheet_storage.ExistingDateMealSheetError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except date_meal_sheet_storage.DateMealSheetStorageError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post(
    "/api/meal-sheets/extract",
    response_model=MealImageExtractionResponse,
)
def extract_meal_sheet_candidates(
    image: UploadFile | None = File(default=None),
    scope: ExtractionScope = Form(default="daily"),
    reference_date: date | None = Form(default=None),
    reference_month: str | None = Form(default=None),
) -> MealImageExtractionResponse:
    image_bytes, mime_type = _validate_meal_image(image)
    normalized_month = _validate_reference_month(reference_month)

    if scope == "daily" and normalized_month is not None:
        raise HTTPException(
            status_code=422,
            detail="하루 급식표에는 날짜 참고값을 사용해 주세요.",
        )
    if scope == "monthly" and reference_date is not None:
        raise HTTPException(
            status_code=422,
            detail="월간 급식표에는 월 참고값을 사용해 주세요.",
        )

    try:
        extraction: GeminiMealExtraction = ai.extract_meal_menus(
            image_bytes,
            mime_type,
            scope,
        )
    except ai.GeminiConfigurationError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ai.GeminiServiceError as exc:
        raise HTTPException(
            status_code=502,
            detail=(
                "Gemini 이미지 추출에 실패했습니다. "
                "기존 저장 데이터는 변경되지 않았습니다. "
                "이미지를 다시 확인하거나 메뉴를 직접 입력해 주세요."
            ),
        ) from exc

    return build_image_extraction_response(
        extraction,
        scope,
        reference_date,
        normalized_month,
    )


@app.post(
    "/api/meal-sheets/{selected_date}/analyze",
    response_model=DateAnalysisResponse,
)
def analyze_date_meal_sheet(selected_date: date) -> DateAnalysisResponse:
    try:
        profile = profile_storage.load_profile()
    except profile_storage.ProfileStorageError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    if not profile["allergies"]:
        raise HTTPException(
            status_code=409,
            detail="먼저 알레르기 정보를 등록해 주세요.",
        )

    try:
        meal_sheet = date_meal_sheet_storage.get_date_meal_sheet(
            selected_date.isoformat()
        )
    except date_meal_sheet_storage.DateMealSheetStorageError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    if meal_sheet["status"] == "NO_DATA":
        raise HTTPException(
            status_code=409,
            detail="선택한 날짜에 저장된 급식 정보가 없습니다.",
        )
    if meal_sheet["status"] == "DRAFT":
        raise HTTPException(
            status_code=409,
            detail="선택한 날짜의 메뉴를 검토 완료로 저장한 뒤 비교해 주세요.",
        )
    if meal_sheet["status"] == "NO_MEAL":
        raise HTTPException(
            status_code=409,
            detail="선택한 날짜는 급식 없음으로 확인되어 비교할 메뉴가 없습니다.",
        )
    if meal_sheet["status"] != "REVIEWED" or not meal_sheet["reviewed"]:
        raise HTTPException(
            status_code=409,
            detail="선택한 날짜의 메뉴를 검토 완료로 저장한 뒤 비교해 주세요.",
        )

    menus = [
        MenuItem(
            id=menu["id"],
            name=menu["name"],
            allergens=(
                tuple(menu["allergens"])
                if menu["allergens"] is not None
                else None
            ),
            is_information_complete=menu["is_information_complete"],
        )
        for menu in meal_sheet["menus"]
    ]
    results = compare_menus(profile["allergies"], menus)

    return DateAnalysisResponse(
        date=selected_date,
        results=results,
        disclaimer=(
            "비교 결과는 선택 날짜의 검토 완료 메뉴에 입력된 표시를 기준으로 합니다. "
            "일치 항목 미확인은 섭취 안전을 보장하지 않습니다. "
            "실제 원재료와 조리 과정은 교육기관 담당자에게 확인해 주세요."
        ),
    )


@app.post("/api/analyze", response_model=AnalysisResponse)
def analyze() -> AnalysisResponse:
    try:
        profile = profile_storage.load_profile()
    except profile_storage.ProfileStorageError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    if not profile["allergies"]:
        raise HTTPException(
            status_code=409,
            detail="먼저 알레르기 정보를 등록해 주세요.",
        )

    try:
        meal_sheet = meal_sheet_storage.load_meal_sheet()
    except meal_sheet_storage.MealSheetStorageError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    if not meal_sheet["reviewed"]:
        raise HTTPException(
            status_code=409,
            detail="급식 메뉴를 검토 완료로 저장한 뒤 비교해 주세요.",
        )

    menus = [
        MenuItem(
            id=menu["id"],
            name=menu["name"],
            allergens=(
                tuple(menu["allergens"])
                if menu["allergens"] is not None
                else None
            ),
            is_information_complete=menu["is_information_complete"],
        )
        for menu in meal_sheet["menus"]
    ]
    results = compare_menus(profile["allergies"], menus)

    return AnalysisResponse(
        results=results,
        disclaimer=(
            "비교 결과는 입력된 급식표 표시를 기준으로 합니다. "
            "일치 항목 미확인은 섭취 안전을 보장하지 않습니다. "
            "실제 원재료와 조리 과정은 교육기관 담당자에게 확인해 주세요."
        ),
    )
