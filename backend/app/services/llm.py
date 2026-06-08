"""Anthropic Claude — 이미지 OCR / 구조화 추출 / 답변 합성."""
import base64 as _b64
import json
import re

import anthropic

from ..core.config import settings

_client: anthropic.Anthropic | None = None


def client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    return _client


def _parse_data_url(data_url: str) -> tuple[str, str]:
    """data:image/png;base64,XXXX → (media_type, raw_b64). 순수 b64면 png로 가정."""
    m = re.match(r"data:(?P<mt>[^;]+);base64,(?P<data>.+)", data_url, re.DOTALL)
    if m:
        return m.group("mt"), m.group("data")
    return "image/png", data_url


def ocr_image(image_data_url: str) -> str:
    media_type, raw = _parse_data_url(image_data_url)
    # 유효성 가벼운 확인
    try:
        _b64.b64decode(raw, validate=True)
    except Exception:
        pass
    resp = client().messages.create(
        model=settings.anthropic_model,
        max_tokens=4096,
        messages=[{
            "role": "user",
            "content": [
                {"type": "image", "source": {"type": "base64", "media_type": media_type, "data": raw}},
                {"type": "text", "text": "이 이미지에 담긴 모든 텍스트와 정보를 빠짐없이 한국어로 추출해줘. 표/코드/UI도 구조를 살려 마크다운으로."},
            ],
        }],
    )
    return "".join(b.text for b in resp.content if b.type == "text").strip()


EXTRACT_TOOL = {
    "name": "save_wiki_entry",
    "description": "입력 내용을 프로젝트 위키 엔트리로 정리하고 온톨로지(엔티티/관계)를 추출한다.",
    "input_schema": {
        "type": "object",
        "properties": {
            "project_name": {
                "type": "string",
                "description": "내용이 속한 프로젝트 이름. 알려진 목록에 있으면 그 이름을 정확히, 없으면 가장 적절한 신규 프로젝트 이름.",
            },
            "title": {"type": "string", "description": "이 엔트리의 주제를 나타내는 짧은 제목. 같은 주제의 후속 업데이트는 동일 제목을 쓴다."},
            "summary_md": {"type": "string", "description": "위키에 기록할 마크다운 본문. 사실 위주로 정리."},
            "occurred_on": {"type": "string", "description": "내용상 사건/업데이트 날짜 (YYYY-MM-DD). 명시 없으면 빈 문자열."},
            "entities": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "type": {"type": "string", "description": "person/tech/component/decision/metric/event 등"},
                    },
                    "required": ["name", "type"],
                },
            },
            "relations": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "subject": {"type": "string"},
                        "predicate": {"type": "string", "description": "관계 술어 (uses/depends_on/owns/replaces 등)"},
                        "object": {"type": "string"},
                    },
                    "required": ["subject", "predicate", "object"],
                },
            },
        },
        "required": ["project_name", "title", "summary_md", "entities", "relations"],
    },
}


def extract(text: str, known_projects: list[str], today: str, hinted_project: str | None) -> dict:
    hint = f"\n사용자가 지정한 프로젝트: {hinted_project} (이 프로젝트로 귀속)." if hinted_project else ""
    known = ", ".join(known_projects) if known_projects else "(없음)"
    resp = client().messages.create(
        model=settings.anthropic_model,
        max_tokens=4096,
        tools=[EXTRACT_TOOL],
        tool_choice={"type": "tool", "name": "save_wiki_entry"},
        messages=[{
            "role": "user",
            "content": (
                f"오늘 날짜: {today}\n알려진 프로젝트: {known}{hint}\n\n"
                f"아래 내용을 프로젝트 위키 엔트리로 정리하고 온톨로지를 추출해줘:\n\n---\n{text}\n---"
            ),
        }],
    )
    for block in resp.content:
        if block.type == "tool_use" and block.name == "save_wiki_entry":
            return block.input
    raise RuntimeError("구조화 추출 실패")


def synthesize(query: str, context: str) -> str:
    resp = client().messages.create(
        model=settings.anthropic_model,
        max_tokens=2048,
        system=(
            "너는 프로젝트 위키 검색 어시스턴트다. 제공된 근거(자료)만 사용해 한국어로 간결히 답하라.\n"
            "각 자료에는 날짜와 버전 맥락이 있다. 같은 주제에서 더 최신 자료가 우선이며, 과거 자료와 다르면 '이전에는 X였으나 현재는 Y' 식으로 변화를 설명하라.\n"
            "근거에 없는 내용은 추측하지 말고 모른다고 답하라. 인용은 [#문서ID] 형식으로 표시하라."
        ),
        messages=[{"role": "user", "content": f"질문: {query}\n\n근거 자료:\n{context}"}],
    )
    return "".join(b.text for b in resp.content if b.type == "text").strip()
