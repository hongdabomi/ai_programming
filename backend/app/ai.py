import base64
import os

import httpx
from google import genai
from google.genai import errors
from pydantic import ValidationError

from backend.app.meal_image_extraction import (
    ExtractionScope,
    GeminiMealExtraction,
)


class GeminiConfigurationError(RuntimeError):
    pass


class GeminiServiceError(RuntimeError):
    pass


EXTRACTION_PROMPT = """
급식표 이미지에서 실제로 보이는 모든 메뉴 행을 찾아 JSON 스키마에 맞게 옮겨 적으세요.
선택 범위는 {scope}이며, 이 값은 메뉴 날짜를 추측하는 근거가 아닙니다.
날짜는 메뉴 행에 명확하게 연결된 경우에만 기록하고, date_text에는 인쇄된 날짜를 그대로 씁니다.
date_iso와 date_has_explicit_year는 이미지에 4자리 연도가 실제로 인쇄된 경우에만 채웁니다.
월/일만 있거나 날짜가 불명확하면 date_iso는 null, date_has_explicit_year는 false로 둡니다.
날짜가 각 메뉴 행과 명확히 연결되지 않으면 해당 메뉴의 날짜를 null로 둡니다.
식사 구분은 명시적인 제목이 메뉴에 연결된 경우에만 설정하고 불분명하면 null로 둡니다.
메뉴명은 이미지에 보이는 그대로 기록하고, 읽을 수 없으면 빈 문자열로 둡니다.
알레르기 표시는 해당 행에 인쇄된 숫자나 기호만 그대로 기록합니다.
①⑤, (1.5), (1,5) 같은 표기를 임의로 항목명으로 바꾸지 마세요.
이미지 안에 알레르기 번호 범례가 있으면 legend_present를 true로 하고 읽을 수 있는 번호와 항목을 모두 적으세요.
범례가 흐리거나 읽을 수 없으면 legend_readable을 false로 설정하세요.
이미지에 없는 날짜, 연도, 메뉴명, 원재료, 알레르기 정보를 추측하지 마세요.
공휴일이나 빈 칸만으로 급식 없음이라고 판단하지 마세요.
메뉴 행을 식별할 수 없으면 menus를 빈 목록으로 반환하세요.
""".strip()


def _required_environment_variable(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise GeminiConfigurationError(
            f"{name} 환경 변수를 설정해야 합니다."
        )
    return value


def create_gemini_client() -> genai.Client:
    api_key = _required_environment_variable("GEMINI_API_KEY")
    return genai.Client(api_key=api_key)


def extract_meal_menus(
    image_bytes: bytes,
    mime_type: str,
    scope: ExtractionScope,
) -> GeminiMealExtraction:
    model = _required_environment_variable("GEMINI_MODEL")
    client = create_gemini_client()
    encoded_image = base64.b64encode(image_bytes).decode("ascii")

    try:
        interaction = client.interactions.create(
            model=model,
            input=[
                {
                    "type": "text",
                    "text": EXTRACTION_PROMPT.format(scope=scope),
                },
                {
                    "type": "image",
                    "data": encoded_image,
                    "mime_type": mime_type,
                },
            ],
            response_format={
                "type": "text",
                "mime_type": "application/json",
                "schema": GeminiMealExtraction.model_json_schema(),
            },
        )
    except (errors.APIError, httpx.RequestError) as exc:
        raise GeminiServiceError(
            "Gemini 이미지 추출 요청에 실패했습니다."
        ) from exc

    output_text = interaction.output_text
    if not output_text:
        raise GeminiServiceError(
            "Gemini가 읽을 수 있는 메뉴 정보를 반환하지 않았습니다."
        )

    try:
        return GeminiMealExtraction.model_validate_json(output_text)
    except (ValidationError, ValueError, TypeError) as exc:
        raise GeminiServiceError(
            "Gemini 응답에서 메뉴 후보를 확인할 수 없습니다."
        ) from exc
