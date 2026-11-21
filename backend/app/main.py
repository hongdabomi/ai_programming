from pathlib import Path
from typing import Literal

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator, model_validator

from backend.app.allergies import ALLERGY_OPTIONS
from backend.app.comparison import MenuItem, compare_menus
from backend.app import meal_sheet_storage, profile_storage

load_dotenv(Path(__file__).resolve().parents[2] / ".env")

app = FastAPI(title="한끼살핌 API")

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


class MealSheetResponse(BaseModel):
    source: Literal["manual"]
    reviewed: bool
    menus: list[MenuInput]


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/allergens")
def get_allergen_options() -> dict[str, tuple[str, ...]]:
    return {"items": ALLERGY_OPTIONS}


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
