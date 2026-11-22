import base64
import json
import os
from datetime import date

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
급식표의 표 구조를 먼저 읽고, 선택한 날짜 칸에 있는 메뉴를 JSON 스키마에 맞게 옮겨 적으세요.
선택 범위는 {scope}입니다. 사용자가 확인하려는 날짜는 {selected_date}입니다.
사용자가 선택한 날짜는 결과 필터 기준이지, 이미지에 인쇄된 실제 날짜라는 증거가 아닙니다.
월간 표에서는 제목의 연도·월, 각 칸 머리의 일자·요일, 그 칸 안의 점심/간식 영역을 함께 읽으세요.
예: 제목이 '2026년 11월 식단표'이고 칸 머리가 '24(화)'이면 그 칸의 메뉴 날짜는 2026-11-24입니다.
선택한 날짜 칸의 음식명은 한 줄씩 모두 읽으세요. 칸 아래의 간식도 별도 메뉴로 포함하세요.
표의 '635/25' 같은 영양 수치, 원산지 표, 알레르기 범례와 안내 문구는 음식명으로 옮기지 마세요.
선택한 날짜와 이미지에서 명확하게 연결되는 메뉴만 반환하세요.
월간 급식표에서는 다른 날짜의 메뉴와 소속 날짜를 확인할 수 없는 메뉴를 반환하지 마세요.
하루 급식표에서 날짜가 인쇄되지 않았지만 한 장이 하루치 메뉴임이 분명하면 메뉴는 반환하고 날짜 필드는 null로 두세요. 저장 날짜는 사용자가 확인합니다.
날짜는 메뉴가 속한 표 칸의 머리와 제목을 근거로 기록합니다. date_text에는 실제 보이는 날짜 근거(예: '2026년 11월 식단표 / 24(화)')를 적으세요.
date_iso와 date_has_explicit_year는 이미지의 표 제목 또는 해당 칸에 4자리 연도가 실제로 인쇄되어 있고, 월·일도 확인된 경우에만 채웁니다.
월/일만 있거나 날짜가 불명확하면 date_iso는 null, date_has_explicit_year는 false로 둡니다.
연도가 없는 월/일 표기는 사용자가 선택한 날짜의 월/일과 같은 경우에만 후보로 포함하고, 연도는 추측하지 마세요.
날짜가 각 메뉴 행과 명확히 연결되지 않으면 해당 메뉴의 날짜를 null로 둡니다.
월간 급식표에서 선택한 날짜와 연결되는지 확인할 수 없는 메뉴는 후보에서 제외하세요.
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
    selected_date: date,
) -> GeminiMealExtraction:
    model = _required_environment_variable("GEMINI_MODEL")
    client = create_gemini_client()
    encoded_image = base64.b64encode(image_bytes).decode("ascii")
    schema_guide = json.dumps(
        GeminiMealExtraction.model_json_schema(),
        ensure_ascii=False,
    )

    prompt = (
        EXTRACTION_PROMPT.format(
            scope=scope,
            selected_date=selected_date.isoformat(),
        )
        + "\n반드시 아래 JSON 구조에 맞는 JSON 객체 하나만 반환하세요."
        + "\n마크다운 코드 블록은 포함하지 마세요.\n"
        + schema_guide
    )
    try:
        interaction = client.interactions.create(
            model=model,
            input=[
                {
                    "type": "text",
                    "text": prompt,
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
