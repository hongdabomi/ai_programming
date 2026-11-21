from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator

from backend.app.allergies import ALLERGY_OPTIONS
from backend.app import profile_storage

load_dotenv(Path(__file__).resolve().parents[2] / ".env")

app = FastAPI(title="한끼살핌 API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5500",
        "http://localhost:5500",
    ],
    allow_methods=["GET", "PUT"],
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
