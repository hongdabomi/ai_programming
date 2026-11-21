from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.app import profile_storage
from backend.app.main import app


@pytest.fixture
def profile_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    path = tmp_path / "data" / "profile.json"
    monkeypatch.setattr(profile_storage, "PROFILE_FILE", path)
    return path


def test_allergen_options_are_available() -> None:
    with TestClient(app) as client:
        response = client.get("/api/allergens")

    assert response.status_code == 200
    items = response.json()["items"]
    assert len(items) == 19
    assert "우유" in items


def test_profile_defaults_to_empty_demo_profile(profile_file: Path) -> None:
    with TestClient(app) as client:
        response = client.get("/api/profile")

    assert response.status_code == 200
    assert response.json() == {"id": "demo-child", "allergies": []}
    assert not profile_file.exists()


def test_profile_persists_multiple_allergies_across_requests(profile_file: Path) -> None:
    selected = ["우유", "대두"]

    with TestClient(app) as client:
        saved = client.put("/api/profile", json={"allergies": selected})

    assert saved.status_code == 200
    assert saved.json() == {"id": "demo-child", "allergies": selected}
    assert profile_file.exists()

    with TestClient(app) as client:
        loaded = client.get("/api/profile")

    assert loaded.status_code == 200
    assert loaded.json() == {"id": "demo-child", "allergies": selected}


def test_profile_can_be_updated_and_cleared(profile_file: Path) -> None:
    with TestClient(app) as client:
        first = client.put("/api/profile", json={"allergies": ["우유", "대두"]})
        updated = client.put("/api/profile", json={"allergies": ["대두", "밀"]})
        cleared = client.put("/api/profile", json={"allergies": []})
        loaded = client.get("/api/profile")

    assert first.status_code == 200
    assert updated.json() == {"id": "demo-child", "allergies": ["대두", "밀"]}
    assert cleared.status_code == 200
    assert cleared.json() == {"id": "demo-child", "allergies": []}
    assert loaded.json() == {"id": "demo-child", "allergies": []}


@pytest.mark.parametrize(
    "allergies",
    [
        ["지원하지 않는 항목"],
        ["우유", "우유"],
    ],
)
def test_profile_rejects_unsupported_or_duplicate_allergies(
    profile_file: Path, allergies: list[str]
) -> None:
    with TestClient(app) as client:
        response = client.put("/api/profile", json={"allergies": allergies})

    assert response.status_code == 422
    assert not profile_file.exists()


def test_profile_reports_corrupt_json_instead_of_using_default(
    profile_file: Path,
) -> None:
    profile_file.parent.mkdir(parents=True)
    profile_file.write_text("{invalid", encoding="utf-8")

    with TestClient(app) as client:
        response = client.get("/api/profile")

    assert response.status_code == 500
    assert response.json()["detail"] == "저장된 알레르기 정보 파일을 읽을 수 없습니다."


def test_profile_reports_storage_write_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    blocking_file = tmp_path / "not-a-directory"
    blocking_file.write_text("blocker", encoding="utf-8")
    monkeypatch.setattr(
        profile_storage, "PROFILE_FILE", blocking_file / "profile.json"
    )

    with TestClient(app) as client:
        response = client.put("/api/profile", json={"allergies": ["우유"]})

    assert response.status_code == 500
    assert response.json()["detail"] == "알레르기 정보를 저장할 수 없습니다."


def test_profile_api_allows_local_frontend_origin(profile_file: Path) -> None:
    with TestClient(app) as client:
        response = client.options(
            "/api/profile",
            headers={
                "Origin": "http://127.0.0.1:5500",
                "Access-Control-Request-Method": "PUT",
                "Access-Control-Request-Headers": "content-type",
            },
        )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == (
        "http://127.0.0.1:5500"
    )
