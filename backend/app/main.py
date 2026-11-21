from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI

load_dotenv(Path(__file__).resolve().parents[2] / ".env")

app = FastAPI(title="한끼살핌 API")


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}
