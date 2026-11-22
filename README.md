# 한끼살핌

**한끼살핌**은 보호자가 자녀의 알레르기 항목과 급식표에 적힌 알레르기 표시를 비교하도록 돕는 웹 서비스입니다. 급식표 이미지는 AI가 날짜·메뉴·표시를 읽는 데 사용하며, 보호자가 내용을 검토해 저장한 뒤 선택한 날짜의 메뉴를 비교합니다.

| 항목 | 내용 |
|---|---|
| 대상 | 식품 알레르기가 있는 자녀의 급식표를 확인하는 보호자 |
| 핵심 흐름 | 알레르기 등록 → 급식표 업로드 또는 저장된 날짜 선택 → 메뉴 검토·저장 → 비교 결과 확인 |
| 기술 | Python, FastAPI, Gemini API, HTML, CSS, JavaScript |
| 현재 상태 | **MVP 일부 구현** — F01·F03과 F05 문의 문구 복사는 구현, F02는 실제 이미지 검증 보완 필요, F04 챗봇은 미구현 |
| 상세 기준 | [PRD.md](./PRD.md) |

> 비교 결과는 급식표의 표시를 기준으로 한 확인 보조 정보입니다. 실제 원재료와 조리 과정은 교육기관 담당자에게 확인해야 합니다.

---

## 빠른 시작

### 실행 환경과 패키지

| 구분 | 요구 사항 |
|---|---|
| 운영 환경 | Python **3.10 이상**, Windows PowerShell 또는 Git Bash. 브라우저와 Git 필요 |
| 백엔드 | `backend/requirements.txt` — FastAPI, Uvicorn, Gemini SDK, Pillow 등 |
| 테스트 | `backend/requirements-dev.txt` — 백엔드 패키지와 pytest, httpx2 |
| AI 이미지 인식 | Gemini API 키와 사용할 모델명 필요. 수동 입력·저장·비교는 키 없이 사용 가능 |
| 실행 주소 | API `http://127.0.0.1:8000` / 웹 화면 `http://127.0.0.1:5500` |

저장소 **루트 폴더**에서 사용하는 터미널에 맞는 명령을 실행합니다.

**PowerShell**

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r backend\requirements-dev.txt
```

**Git Bash**

```bash
py -3 -m venv .venv
source .venv/Scripts/activate
python -m pip install -r backend/requirements-dev.txt
```

이미지 인식을 사용한다면 `.env.example`을 복사해 `.env`를 만들고 본인의 값을 입력합니다. 기존 `.env`가 있으면 덮어쓰지 마세요. `.env`는 Git에서 제외됩니다.

**PowerShell**

```powershell
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
```

**Git Bash**

```bash
if [ ! -f .env ]; then cp .env.example .env; fi
```

```dotenv
GEMINI_API_KEY=본인의_API_키
GEMINI_MODEL=사용할_모델명
```

### 서버 실행

PowerShell과 Git Bash 중 **하나를 선택**해 API 서버와 웹 화면을 각각 별도 창에서 실행합니다.

**PowerShell 창 1 — API 서버**

```powershell
python -m uvicorn backend.app.main:app --reload
```

**Git Bash 창 1 — API 서버**

```bash
python -m uvicorn backend.app.main:app --reload
```

**PowerShell 창 2 — 웹 화면**

```powershell
python -m http.server 5500 --directory frontend
```

**Git Bash 창 2 — 웹 화면**

```bash
python -m http.server 5500 --directory frontend
```

브라우저에서 **http://127.0.0.1:5500**을 엽니다. API 동작 확인은 `http://127.0.0.1:8000/health`에서 할 수 있습니다.

---

## 사용 방법

| 순서 | 화면 | 사용자가 하는 일 |
|---|---|---|
| 1 | 홈·알레르기 정보 | 가상 프로필에서 알레르기 항목을 선택하고 저장합니다. |
| 2 | 급식표 유형 | 하루 급식표, 한 달 급식표, 이전에 저장한 급식표 중 하나를 선택합니다. |
| 3 | 업로드·날짜 선택 | JPG·JPEG·PNG 파일을 올립니다. 월간 급식표는 확인할 날짜를 선택합니다. 이미지 인식에는 Gemini 설정이 필요합니다. |
| 4 | 인식 결과·메뉴 검토 | AI가 읽은 날짜·메뉴·알레르기 표시를 원본과 대조합니다. 잘못 읽은 내용은 수정하고 검토 완료로 저장합니다. 인식에 실패하면 메뉴를 직접 입력할 수 있습니다. |
| 5 | 비교 결과 | 저장된 알레르기와 해당 날짜의 검토 완료 메뉴를 비교합니다. 필요한 메뉴에 대해 교사에게 보낼 확인 요청 문구를 복사할 수 있습니다. |

이미 저장된 날짜는 이미지를 다시 올리지 않고 선택해 조회할 수 있습니다. 날짜별 상태는 **정보 없음 / 검토 전 / 검토 완료 / 급식 없음**으로 구분하며, 검토 완료된 메뉴만 비교합니다.

### 실행 화면 스크린샷

> 아래의 **이미지 추가 예정** 칸은 실행 화면을 직접 캡처한 뒤 채우는 자리입니다. 사진 파일을 저장소에 넣을 경우 상대 경로(예: `docs/screenshots/home.png`)로 연결하세요.

| 화면 | 확인할 내용 | 스크린샷 |
|---|---|---|
| 홈 | 서비스 소개와 시작 버튼 | **이미지 추가 예정** |
| 알레르기 등록 | 항목 선택·저장 상태 | **이미지 추가 예정** |
| 급식표 업로드·날짜 선택 | 일간 또는 월간 이미지 경로 | **이미지 추가 예정** |
| 인식 결과·메뉴 검토 | 후보 수정과 검토 완료 | **이미지 추가 예정** |
| 알레르기 비교 결과 | 등록 항목 중심의 주의·확인 결과 | **이미지 추가 예정** |

---

## MVP 체크리스트

상태는 **현재 코드에서 확인되는 범위**를 기준으로 적었습니다. 계획서의 실물 이미지·수동 데모 검증은 코드 구현과 별개로 표시합니다.

| ID | 중간고사 계획의 MVP 기능 | 상태 | 근거 / 남은 일 |
|---|---|---|---|
| F01 | 알레르기 정보 등록·조회·수정 | **완료** | 다중 선택·저장·재조회 API와 화면 구현. 실제 아동 정보 대신 가상 프로필 사용 |
| F02 | 급식표 이미지 업로드, AI 추출, 사용자 수정 | **부분 완료** | 일간·월간 업로드, 날짜별 후보, 메뉴 수정·저장 및 오류 안내 구현. 계획서 기준 **테스트 이미지 5개 수동 검증**과 오인식 사례 확인은 추가 필요 |
| F03 | 등록 알레르기와 급식표 표시 비교 | **완료** | 선택 날짜의 검토 완료 메뉴를 규칙 기반으로 비교. 일치·정보 부족·일치 미확인 사례 테스트 포함 |
| F04 | 확인된 정보를 근거로 답하는 AI 챗봇 | **미완료** | 화면의 AI 도우미는 준비 중. 계획서의 질문 5개 검증도 미수행 |
| F05 | 교사·급식 담당자 문의 문구 복사 | **구현** | 선택 날짜와 등록 알레르기·주의 메뉴를 반영한 문구 복사 기능. 중간 계획에서는 후순위 |

**전체 MVP는 아직 완료되지 않았습니다.** 특히 F04와 F02의 계획서 기준 실물 이미지 검증이 남아 있습니다.

---

## 중간고사 계획에서 변경된 내용

| 변경 사항 | 중간 계획 | 현재 내용과 이유 |
|---|---|---|
| 서비스명 | `아이밥지킴(가칭)` | **한끼살핌**으로 확정. 화면·문서의 이름을 통일 |
| 급식표 저장 단위 | 이미지 업로드와 메뉴 검토 중심 | 날짜가 없거나 여러 날짜가 한 이미지에 있는 경우를 다루기 위해 **날짜별 저장·조회**를 추가 |
| 재방문 흐름 | 업로드 중심 | 이미 검토한 급식표를 다시 올리지 않도록 **저장 날짜 선택·재사용** 경로를 추가 |
| 날짜별 상태 | 별도 상태 구분이 구체적이지 않음 | 정보 없음·검토 전·검토 완료·급식 없음을 구분해 잘못된 날짜의 메뉴를 비교하지 않도록 함 |
| 구현 순서 | 필수 F01~F04 후 F05 검토 | F04 챗봇 전에 F05 문의 문구 복사가 구현됨. 챗봇 미구현 상태를 완료로 표시하지 않음 |
| 화면 구성 | 기능 우선 화면 | 제공된 화면 구현 예시를 바탕으로 단계별 화면과 모바일 배치를 정리 |

변경 배경과 완료 조건의 상세 내용은 [PRD의 변경 기록](./PRD.md#12-계획과-구현-제안의-구분-및-변경-기록)을 참고하세요.

---

## 테스트와 검증

저장소 루트에서 실행합니다.

**PowerShell**

```powershell
python -m pytest -q
```

**Git Bash**

```bash
python -m pytest -q
```

최근 로컬 실행 결과는 **111개 통과**입니다. 테스트는 프로필 저장, 날짜별 급식표, 이미지 후보 처리, 알레르기 번호 비교, API 오류 등 코드 동작을 다룹니다. 외부 Gemini 호출은 모의 응답으로 검증하므로 **실제 이미지 5개에 대한 인식 품질 검증을 대신하지 않습니다.**

| 추가 확인 항목 | 기록 칸 |
|---|---|
| 실제 이미지 5개 업로드·수정 결과 | **검증 후 작성 예정** |
| 챗봇 질문 5개 | **F04 구현 후 작성 예정** |
| 모바일 실행 화면·데모 | **스크린샷 및 결과 추가 예정** |

---

## 개발 과정과 증빙

사진은 직접 넣을 수 있도록 자리만 마련했습니다. 각 사례의 설명도 실제로 사용한 프롬프트·오류·리뷰 내용에 맞춰 **1~2문장으로 작성**하세요.

| 사례 | 설명 입력 칸 | 스크린샷 |
|---|---|---|
| Copilot Chat 활용 | **작성 예정:** 사용한 질문, 받은 제안, 실제 채택·수정한 부분 | **사진 추가 예정** |
| 디버깅 | **작성 예정:** 발생한 오류, 원인 확인 방법, 수정 결과 | **사진 추가 예정** |
| 코드 리뷰 반영 | **작성 예정:** 받은 의견, 바꾼 코드, 재검증 결과 | **사진 추가 예정** |

---

## 코드와 데이터 구성

| 위치 | 역할 |
|---|---|
| `frontend/index.html` · `style.css` · `script.js` | 화면 구조·스타일·사용 흐름 |
| `frontend/assets/` | 화면에서 사용하는 로고와 홈 이미지 |
| `backend/app/main.py` | FastAPI 엔드포인트와 요청 검증 |
| `backend/app/ai.py` · `meal_image_extraction.py` | Gemini 이미지 추출과 날짜·알레르기 번호 후보 처리 |
| `backend/app/comparison.py` · `allergies.py` | 저장된 알레르기와 메뉴 표시의 규칙 기반 비교 |
| `backend/app/*storage.py` | 가상 프로필과 급식표 JSON 저장·조회 |
| `backend/tests/` | API·저장·비교·이미지 처리 테스트 |
| `PRD.md` | 요구사항, 수용 기준, 계획 변경 기록 |

프로필은 `backend/data/profile.json`, 날짜별 급식표는 `backend/data/meal_sheets.json`에 로컬 저장됩니다. `backend/data/meal_sheet.json`은 기존 날짜 미지정 급식표를 위한 호환 파일입니다. 이 데이터와 실제 급식표 이미지는 **실행 자료**이며 README 스크린샷 자리와 별개입니다.

### 주요 API

| 메서드 | 경로 | 용도 |
|---|---|---|
| `GET` / `PUT` | `/api/profile` | 가상 프로필의 알레르기 조회·저장 |
| `GET` | `/api/meal-sheets?month=YYYY-MM` | 해당 월의 저장 날짜·상태 조회 |
| `GET` / `PUT` | `/api/meal-sheets/{date}` | 날짜별 메뉴 조회·저장 |
| `POST` | `/api/meal-sheets/extract` | 이미지에서 검토 전 후보 추출 |
| `POST` | `/api/meal-sheets/{date}/analyze` | 선택 날짜의 검토 완료 메뉴 비교 |
| `GET` | `/health` | API 상태 확인 |

문서 형식은 [GitHub의 README 안내](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-readmes)와 [Markdown 표 작성 안내](https://docs.github.com/en/get-started/writing-on-github/working-with-advanced-formatting/organizing-information-with-tables)를 참고했습니다.
