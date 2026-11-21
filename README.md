# 한끼살핌

보호자가 급식표에 표시된 알레르기 정보를 확인하도록 돕는 웹 서비스입니다. 음식의 안전성을 판정하거나 보장하지 않습니다. 상세 요구사항과 안전 원칙은 [PRD.md](./PRD.md)를 참고하세요.

## 현재 상태

초기 개발 환경만 구성되어 있습니다. 프론트엔드 화면은 안내용 골격이고, 백엔드는 실행 확인용 `/health`만 제공합니다. 알레르기 등록, 이미지 분석, 비교, 챗봇 등 MVP 기능은 아직 구현하지 않았습니다.

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
│   │   └── main.py
│   └── requirements.txt
├── frontend/
│   └── index.html
├── .env.example
├── .gitignore
└── PRD.md
```

- `frontend/`: HTML, CSS, JavaScript 기반 웹 화면
- `backend/app/main.py`: FastAPI 애플리케이션과 상태 확인 경로
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
python -m pip install -r backend\requirements.txt
```

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

프론트엔드 안내 화면은 `frontend\index.html`을 브라우저에서 열거나, 저장소 루트에서 아래 명령으로 확인할 수 있습니다.

```powershell
python -m http.server 5500 --directory frontend
```

그 후 `http://127.0.0.1:5500`을 엽니다. 현재 프론트엔드는 백엔드와 연결되어 있지 않습니다.

## 검증

현재 자동화 테스트나 린터는 추가하지 않았습니다. Python 구문 확인은 다음과 같이 실행할 수 있습니다.

```powershell
python -m compileall backend
```

기능을 추가할 때에는 PRD의 완료 조건과 예외 처리 기준을 테스트로 검증하고, 실행한 명령과 결과를 변경 요약에 기록하세요.
