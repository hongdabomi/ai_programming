import json
import tempfile
from pathlib import Path
from typing import TypedDict

from backend.app.allergies import ALLERGY_OPTIONS

PROFILE_ID = "demo-child"
PROFILE_FILE = Path(__file__).resolve().parents[1] / "data" / "profile.json"


class AllergyProfile(TypedDict):
    id: str
    allergies: list[str]


class ProfileStorageError(Exception):
    pass


def load_profile() -> AllergyProfile:
    try:
        with PROFILE_FILE.open(encoding="utf-8") as file:
            profile = json.load(file)
    except FileNotFoundError:
        return {"id": PROFILE_ID, "allergies": []}
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ProfileStorageError(
            "저장된 알레르기 정보 파일을 읽을 수 없습니다."
        ) from exc

    if not isinstance(profile, dict):
        raise ProfileStorageError("저장된 알레르기 정보 형식이 올바르지 않습니다.")

    allergies = profile.get("allergies")
    if (
        profile.get("id") != PROFILE_ID
        or not isinstance(allergies, list)
        or any(
            not isinstance(item, str) or item not in ALLERGY_OPTIONS
            for item in allergies
        )
        or len(allergies) != len(set(allergies))
    ):
        raise ProfileStorageError("저장된 알레르기 정보 형식이 올바르지 않습니다.")

    return {"id": PROFILE_ID, "allergies": allergies}


def save_profile(allergies: list[str]) -> AllergyProfile:
    profile: AllergyProfile = {"id": PROFILE_ID, "allergies": allergies}
    temporary_path: Path | None = None
    try:
        PROFILE_FILE.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=PROFILE_FILE.parent,
            prefix=".profile-",
            suffix=".tmp",
            delete=False,
        ) as file:
            temporary_path = Path(file.name)
            json.dump(profile, file, ensure_ascii=False, indent=2)
            file.write("\n")
        temporary_path.replace(PROFILE_FILE)
    except (OSError, UnicodeError) as exc:
        raise ProfileStorageError("알레르기 정보를 저장할 수 없습니다.") from exc
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)

    return profile
