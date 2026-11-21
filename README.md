# 한끼살핌

보호자가 급식표에 표시된 알레르기 정보를 확인하도록 돕는 웹 서비스입니다. 음식의 안전성을 판정하거나 보장하지 않습니다. 상세 요구사항과 안전 원칙은 [PRD.md](./PRD.md)를 참고하세요.

## 현재 상태

F01 알레르기 정보 등록을 구현했습니다. 알레르기 선택 항목을 저장·조회·수정할 수 있으며, 프로필은 로컬 JSON 파일에 보관됩니다. 급식표 이미지 분석, 알레르기 비교, 챗봇 등 나머지 MVP 기능은 아직 구현하지 않았습니다.

## 구성

```text
.
├── .github/
│   ├── copilot-instructions.md
│   └── skills/
│       ├── create-pr/SKILL.md
│       └── git-commit/SKILL.md
├── backend/
│   ├── app/
│   │   ├── ai.py
│   │   ├── allergies.py
│   │   ├── main.py
│   │   └── profile_storage.py
│   ├── tests/
│   │   ├── test_main.py
│   │   └── test_profile.py
│   ├── requirements.txt
│   └── requirements-dev.txt
├── frontend/
│   └── index.html
├── backend/data/profile.json  # 실행 후 생성되는 로컬 데이터 (Git 제외)
├── pytest.ini
├── .env.example
├── .gitignore
└── PRD.md
```

- `frontend/`: HTML, CSS, JavaScript 기반 웹 화면
- `backend/app/main.py`: FastAPI 애플리케이션, `/health` 및 알레르기 프로필 API
- `backend/app/allergies.py`: 학교 급식 알레르기 표시 19종 선택 항목
- `backend/app/profile_storage.py`: 데모 프로필 JSON 읽기·쓰기
- `backend/app/ai.py`: Gemini 클라이언트 생성 경계. 모델 호출/제품 기능은 아직 없음
- `.github/`: 저장소용 Copilot 지침과 반복 작업 스킬

## 개발 환경

- Python 3.10 이상
- Git
- VS Code (선택)
- Gemini API 키는 실제 AI 연동을 개발할 때만 필요합니다.

PowerShell에서 저장소 루트 기준으로 실행합니다.

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r backend\requirements-dev.txt
```

`requirements-dev.txt`에는 백엔드 의존성과 테스트용 `pytest`, `httpx2`가 포함됩니다. 런타임 의존성만 설치하려면 `backend\requirements.txt`를 사용하세요.

`.env.example`을 참고해 루트에 `.env`를 만들고, 실제 키가 있을 때만 `GEMINI_API_KEY` 값을 설정하세요. 기존 `.env`가 있다면 덮어쓰지 마세요. `.env`는 Git에서 제외됩니다.

```powershell
if (-not (Test-Path .env)) {
    Copy-Item .env.example .env
} else {
    Write-Host ".env already exists; leaving it unchanged."
}
```

API 서버 실행:

```powershell
python -m uvicorn backend.app.main:app --reload
```

별도 PowerShell에서 상태 확인:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health
```

프론트엔드에서 API를 사용하려면 별도 PowerShell 창에서 정적 서버를 실행합니다.

```powershell
python -m http.server 5500 --directory frontend
```

그 후 브라우저에서 `http://127.0.0.1:5500`을 엽니다. API와 프론트엔드는 각각 8000, 5500 포트에서 실행해야 합니다.

데모 프로필은 `backend\data\profile.json`에 저장되어 서버를 다시 실행해도 유지됩니다. 이 파일은 로컬 전용이며 Git에서 제외됩니다. 실제 아동의 이름이나 건강정보를 입력하지 마세요. 현재는 가상 프로필 `테스트 자녀`만 사용합니다.

F01 API:

| Method | Path | 동작 |
|---|---|---|
| `GET` | `/api/allergens` | 선택 가능한 알레르기 항목 조회 |
| `GET` | `/api/profile` | 저장된 데모 프로필 조회 |
| `PUT` | `/api/profile` | `{ "allergies": ["우유", "대두"] }` 형식으로 전체 선택값 저장·수정 |

빈 `allergies` 목록은 허용됩니다. 지원하지 않는 항목이나 중복 항목은 `422` 응답으로 거부합니다.

## 검증

테스트 실행:

```powershell
python -m pytest
```

`/health`와 F01 프로필 API의 정상·예외 동작 테스트가 포함되어 있습니다. Python 구문 확인은 다음과 같이 실행할 수 있습니다.

```powershell
python -m compileall backend
```

린터는 아직 설정되어 있지 않습니다. 기능을 추가할 때에는 PRD의 완료 조건과 예외 처리 기준을 테스트로 검증하고, 실행한 명령과 결과를 변경 요약에 기록하세요.
