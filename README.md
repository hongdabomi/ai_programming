# 한끼살핌

보호자가 급식표에 표시된 알레르기 정보를 확인하도록 돕는 웹 서비스입니다. 음식의 안전성을 판정하거나 보장하지 않습니다. 상세 요구사항과 안전 원칙은 [PRD.md](./PRD.md)를 참고하세요.

## 현재 상태

F01 알레르기 정보 등록, F02 급식 메뉴 수동 입력·검토, 날짜별 JSON 저장·조회와 Gemini 이미지 후보 추출, F03 선택 날짜의 검토 완료 메뉴 비교를 구현했습니다. 화면 흐름은 알레르기 등록 → 급식표 유형 선택 → 하루 이미지 업로드 또는 월간 이미지 업로드·날짜 선택 → 인식 결과 검토 → 비교 결과 순서입니다. 비교 결과 화면에서 선택 날짜의 메뉴와 알레르기 항목을 담은 문의 문구를 복사할 수 있습니다(F05). Gemini 추출은 날짜·메뉴·알레르기 표시 후보만 반환하며, 사용자가 검토 화면에서 날짜와 내용을 확인해 저장하기 전에는 기존 급식표나 F03 비교에 반영되지 않습니다. 기존 날짜 미지정 급식표 비교도 호환 경로로 유지합니다. F04 챗봇은 아직 구현하지 않았습니다.

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
│   │   ├── comparison.py
│   │   ├── date_meal_sheet_storage.py
│   │   ├── meal_image_extraction.py
│   │   ├── main.py
│   │   ├── meal_sheet_storage.py
│   │   └── profile_storage.py
│   ├── tests/
│   │   ├── test_comparison.py
│   │   ├── test_date_meal_sheets.py
│   │   ├── test_meal_sheet.py
│   │   ├── test_main.py
│   │   └── test_profile.py
│   ├── requirements.txt
│   └── requirements-dev.txt
├── frontend/
│   ├── index.html
│   ├── style.css
│   └── script.js
├── backend/data/profile.json  # 실행 후 생성되는 로컬 데이터 (Git 제외)
├── backend/data/meal_sheet.json  # 기존 날짜 미지정 급식표 (Git 제외)
├── backend/data/meal_sheets.json  # 날짜별 급식표 JSON (Git 제외)
├── pytest.ini
├── .env.example
├── .gitignore
└── PRD.md
```

- `frontend/`: HTML, CSS, JavaScript 기반 웹 화면
- `backend/app/main.py`: FastAPI 애플리케이션, 상태·프로필·급식표·비교 API
- `backend/app/allergies.py`: 학교 급식 알레르기 표시 19종 선택 항목
- `backend/app/profile_storage.py`: 데모 프로필 JSON 읽기·쓰기
- `backend/app/meal_sheet_storage.py`: 기존 날짜 미지정 급식표 JSON과 검토 상태 관리
- `backend/app/date_meal_sheet_storage.py`: 날짜별 급식표 JSON 저장·조회 및 기존 데이터 미지정 보존
- `backend/app/comparison.py`: 검토 완료 메뉴와 저장된 프로필의 규칙 기반 비교
- `backend/app/ai.py`: 환경변수 기반 Gemini 이미지 추출 호출
- `backend/app/meal_image_extraction.py`: 구조화된 날짜·메뉴 후보와 알레르기 번호 대응 검증
- `.github/`: 저장소용 Copilot 지침과 반복 작업 스킬

## 개발 환경

- Python 3.10 이상
- Git
- VS Code (선택)
- Gemini 이미지 추출을 실제 호출하려면 API 키와 모델명을 설정해야 합니다.

PowerShell에서 저장소 루트 기준으로 실행합니다.

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r backend\requirements-dev.txt
```

`requirements-dev.txt`에는 백엔드 의존성과 테스트용 `pytest`, `httpx2`가 포함됩니다. 런타임 의존성만 설치하려면 `backend\requirements.txt`를 사용하세요.

`.env.example`을 참고해 루트에 `.env`를 만들고 `GEMINI_API_KEY`, `GEMINI_MODEL`을 설정하세요. 기존 `.env`가 있다면 덮어쓰지 마세요. 실제 API 키는 소스나 로그에 기록하지 않으며, `.env`는 Git에서 제외됩니다.

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

데모 프로필은 `backend\data\profile.json`, 새 날짜별 급식표는 `backend\data\meal_sheets.json`에 저장되어 서버를 다시 실행해도 유지됩니다. 이 파일들은 로컬 전용이며 Git에서 제외됩니다. 기존 `backend\data\meal_sheet.json`은 삭제하거나 수정하지 않습니다. 날짜가 없는 기존 메뉴는 별도의 미지정 영역에 보존되며, 날짜를 자동 지정하지 않습니다. 화면에서 사용자가 날짜를 선택해 초안으로 복사하고 저장한 뒤에만 날짜별 데이터가 됩니다. 실제 아동의 이름이나 건강정보를 입력하지 마세요. 현재는 가상 프로필 `테스트 자녀`만 사용합니다.

F01 API:

| Method | Path | 동작 |
|---|---|---|
| `GET` | `/api/allergens` | 선택 가능한 알레르기 항목 조회 |
| `GET` | `/api/profile` | 저장된 데모 프로필 조회 |
| `PUT` | `/api/profile` | `{ "allergies": ["우유", "대두"] }` 형식으로 전체 선택값 저장·수정 |

`GET /api/allergens`는 선택 항목과 함께 급식 알레르기 번호 1~19의 명시적 대응표를 반환합니다.

빈 `allergies` 목록은 허용됩니다. 지원하지 않는 항목이나 중복 항목은 `422` 응답으로 거부합니다.

급식표 수동 입력·비교 API:

| Method | Path | 동작 |
|---|---|---|
| `GET` | `/api/meal-sheets?month=YYYY-MM` | 해당 월에 저장된 날짜와 상태 목록 조회 |
| `GET` | `/api/meal-sheets/{date}` | 날짜별 급식표 조회. 기록이 없으면 `NO_DATA` 반환 |
| `PUT` | `/api/meal-sheets/{date}` | 날짜별 메뉴 초안·검토 완료·급식 없음 저장 |
| `GET` | `/api/meal-sheets/unassigned` | 날짜가 없는 기존 급식표 보존 데이터 조회 |
| `GET/PUT` | `/api/meal-sheets/current` | 기존 날짜 미지정 급식표 호환 API |
| `POST` | `/api/meal-sheets/extract` | JPG/JPEG/PNG 이미지의 날짜·메뉴·알레르기 표시 후보 추출 (저장하지 않음) |
| `POST` | `/api/analyze` | 기존 날짜 미지정 급식표의 기존 비교 API |
| `POST` | `/api/meal-sheets/{date}/analyze` | 선택 날짜의 검토 완료된 전체 메뉴와 등록 알레르기 비교 |

날짜별 저장 상태는 `NO_DATA`(정보 없음), `DRAFT`(검토 전), `REVIEWED`(검토 완료), `NO_MEAL`(사용자 확인 후 급식 없음)으로 구분합니다. 날짜별 분석은 `REVIEWED`만 허용하며 다른 상태는 `409`와 상태 안내를 반환합니다. 기존 날짜를 다시 저장할 때는 요청의 `replace_existing: true`가 없으면 `409`로 거부하며, 화면에서 사용자에게 덮어쓰기를 확인합니다. 날짜 없는 기존 데이터는 `unassigned`로 보존하고 원본 `meal_sheet.json`도 수정하지 않습니다. 기존 `/api/analyze`는 날짜 없는 급식표에 대한 호환 비교 경로입니다.

이미지 추출 API는 multipart 형식으로 `image`, `scope`(`daily` 또는 `monthly`), 필수 `selected_date`와 일간 `reference_date` 또는 월간 `reference_month`를 받습니다. Gemini와 서버는 선택한 날짜에 명확히 연결된 메뉴만 후보로 반환하며, 다른 날짜와 날짜를 식별할 수 없는 월간 메뉴는 제외합니다. 이미지에 연도가 없더라도 인쇄된 월/일이 선택 날짜와 일치하면 후보로 보여줄 수 있지만, 실제 날짜는 `null`로 유지하고 저장 날짜는 사용자가 직접 확인해야 합니다. 날짜를 식별하지 못하거나 일치 후보가 없으면 급식 없음으로 확정하지 않고 확인 안내를 반환합니다. 번호 표기는 기존 1~19 대응표를 사용하며 이미지 범례가 불일치하거나 불명확하면 항목명 변환 대신 추가 확인을 요구합니다. 추출 결과는 사용자 검토 전 후보이며 JSON 저장소에 기록되지 않습니다. 실제 Gemini API 호출은 키와 모델 환경변수가 필요하고, 테스트에서는 모의 응답을 사용합니다.

## 검증

테스트 실행:

```powershell
python -m pytest
```

`/health`, 프로필·급식표 저장 및 비교 API의 정상·예외 동작 테스트가 포함되어 있습니다. Python 구문 확인은 다음과 같이 실행할 수 있습니다.

```powershell
python -m compileall backend
```

린터는 아직 설정되어 있지 않습니다. 기능을 추가할 때에는 PRD의 완료 조건과 예외 처리 기준을 테스트로 검증하고, 실행한 명령과 결과를 변경 요약에 기록하세요.
