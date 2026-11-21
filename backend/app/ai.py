import os

from google import genai


def create_gemini_client() -> genai.Client:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY 환경 변수를 설정해야 합니다.")
    return genai.Client(api_key=api_key)
