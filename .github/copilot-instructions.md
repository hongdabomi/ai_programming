# 한끼살핌 저장소 지침

## 프로젝트와 기술 스택

- 한끼살핌은 보호자가 어린이 급식표의 알레르기 정보를 확인하도록 돕는 웹 서비스다. 세부 요구사항은 저장소 루트의 `PRD.md`를 기준으로 한다.
- 프론트엔드는 HTML, CSS, JavaScript, 백엔드는 Python과 FastAPI, 초기 데모 저장은 JSON, AI 보조 연동은 Gemini API를 사용한다. 필요성이 PRD에 명시되지 않은 프레임워크, 데이터베이스, 인증 기능은 추가하지 않는다.
- 현재 저장소는 초기 골격이다. MVP 기능을 요청받지 않았다면 알레르기 등록, 이미지 추출, 비교, 챗봇 등의 기능을 선제 구현하지 않는다.

## 구조와 실행

- `frontend/`: 정적 웹 화면
- `backend/app/main.py`: FastAPI 앱 및 `/health`
- `backend/app/ai.py`: Gemini 클라이언트 생성 경계
- `backend/requirements.txt`: Python 의존성
- 루트 `.env.example`: 필요한 환경변수 이름만 제공. 실제 키는 `.env`에만 저장한다.
- 개발 환경은 Python 3.10 이상과 PowerShell을 기준으로 한다. 설치는 `py -3 -m venv .venv`, `.\.venv\Scripts\Activate.ps1`, `python -m pip install -r backend\requirements.txt` 순서다.
- API 실행: `python -m uvicorn backend.app.main:app --reload`; 상태 확인: `Invoke-RestMethod http://127.0.0.1:8000/health`.
- 프론트엔드 확인: `python -m http.server 5500 --directory frontend` 후 `http://127.0.0.1:5500`을 연다. 프론트엔드는 현재 API와 연결되어 있지 않다.
- 변경 후 최소 `python -m compileall backend`를 실행한다. 테스트와 린터는 아직 설정되어 있지 않으므로, 기능을 추가할 때 범위에 맞는 자동화 테스트를 함께 구성하고 실행 결과를 보고한다.

## 구현 원칙

- PRD의 범위, 데이터 흐름, 완료 조건을 먼저 확인하고 작고 검증 가능한 변경을 한다. 불필요한 폴더와 규칙 파일을 추가하지 않는다.
- Gemini 추출은 후보 정보일 뿐이다. 사용자가 검토·수정한 데이터만 비교 입력으로 사용하고, AI 추론으로 확정 정보를 덮어쓰지 않는다.
- `MATCH`, `CHECK_NEEDED`, `NOT_IDENTIFIED`를 구분한다. 일치가 확인되지 않았다는 결과를 안전 판정으로 표현하지 말고, 정보가 부족하면 추가 확인을 안내한다. 의료적 진단이나 섭취 안전을 보장하지 않는다.
- 테스트와 데모에는 가상 데이터를 사용한다. 실제 아동 개인정보, API 키, 기타 비밀정보를 소스나 로그에 넣지 않는다.
- 환경변수 누락과 API 오류는 명확히 알리고, 조용한 기본값이나 성공처럼 보이는 대체 결과로 숨기지 않는다.
- 사용자 승인 없이 Git commit 또는 push를 수행하거나 Pull Request를 만들지 않는다. 요청 범위 밖의 파일을 stage하지 않는다.

## 변경 보고

변경한 파일과 이유, 실행한 검증 명령 및 결과, 수행하지 못한 검증을 간결하게 보고한다. 문서와 코드의 설정이 달라지면 관련 문서도 함께 갱신한다.
