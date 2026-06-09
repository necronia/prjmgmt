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


_OCR_PROMPT = "이 이미지에 담긴 모든 텍스트와 정보를 빠짐없이 한국어로 추출해줘. 표/코드/UI도 구조를 살려 마크다운으로."


def ocr_image_bytes(data: bytes, media_type: str) -> str:
    raw = _b64.b64encode(data).decode()
    resp = client().messages.create(
        model=settings.anthropic_model,
        max_tokens=4096,
        messages=[{
            "role": "user",
            "content": [
                {"type": "image", "source": {"type": "base64", "media_type": media_type, "data": raw}},
                {"type": "text", "text": _OCR_PROMPT},
            ],
        }],
    )
    return "".join(b.text for b in resp.content if b.type == "text").strip()


def ocr_image(image_data_url: str) -> str:
    media_type, raw = _parse_data_url(image_data_url)
    try:
        return ocr_image_bytes(_b64.b64decode(raw), media_type)
    except Exception:
        # 이미 raw base64 가 깨졌을 경우 대비 — 원본 그대로 재시도
        raw_bytes = raw.encode() if isinstance(raw, str) else raw
        return ocr_image_bytes(raw_bytes, media_type)


MERGE_TOOL = {
    "name": "update_project_wiki",
    "description": "프로젝트의 단일 위키 문서에 새 입력을 병합해 갱신본을 만들고 온톨로지(엔티티/관계)를 추출한다.",
    "input_schema": {
        "type": "object",
        "properties": {
            "project_name": {
                "type": "string",
                "description": "내용이 속한 프로젝트 이름. 알려진 목록에 있으면 그 이름을 정확히, 없으면 가장 적절한 신규 프로젝트 이름.",
            },
            "content_md": {
                "type": "string",
                "description": (
                    "프로젝트 위키 '전체' 본문(마크다운). 기존 본문에 새 정보를 자연스럽게 병합한 갱신본 전체를 반환한다. "
                    "기존 내용은 보존하되, 같은 항목이 갱신되면 최신으로 바꾸고 변경/추가된 사실에는 문장 끝에 `(YYYY-MM-DD 수정)` 또는 `(YYYY-MM-DD 추가)` 표기를 붙여 명시한다. "
                    "주제별 섹션(##)으로 구조화한다. 별도의 변경이력 섹션은 만들지 않는다(수정 이력은 시스템이 따로 관리)."
                ),
            },
            "change_summary": {
                "type": "string",
                "description": "이번 입력으로 추가/변경된 핵심을 1~3줄로 요약 (수정 이력에 기록됨).",
            },
            "occurred_on": {"type": "string", "description": "이번 변경 사건의 날짜 (YYYY-MM-DD). 내용에 명시 없으면 빈 문자열(오늘로 처리)."},
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
        "required": ["project_name", "content_md", "change_summary", "entities", "relations"],
    },
}


def merge(existing_md: str, new_text: str, known_projects: list[str], today: str, hinted_project: str | None) -> dict:
    hint = f"\n사용자가 지정한 프로젝트: {hinted_project} (이 프로젝트로 귀속)." if hinted_project else ""
    known = ", ".join(known_projects) if known_projects else "(없음)"
    existing_block = existing_md.strip() or "(아직 위키 없음 — 새로 작성)"
    resp = client().messages.create(
        model=settings.anthropic_model,
        max_tokens=8192,
        tools=[MERGE_TOOL],
        tool_choice={"type": "tool", "name": "update_project_wiki"},
        messages=[{
            "role": "user",
            "content": (
                f"오늘 날짜: {today}\n알려진 프로젝트: {known}{hint}\n\n"
                f"=== 기존 프로젝트 위키 본문 ===\n{existing_block}\n\n"
                f"=== 새로 들어온 입력 ===\n{new_text}\n\n"
                "위 새 입력을 기존 위키 본문에 병합해 '전체 갱신본'을 만들고, 변경/추가 사실에 날짜 표기를 붙여라. "
                "이번 변경 요약과 온톨로지(엔티티/관계)도 추출하라."
            ),
        }],
    )
    for block in resp.content:
        if block.type == "tool_use" and block.name == "update_project_wiki":
            return block.input
    raise RuntimeError("위키 병합 실패")


def synthesize(query: str, context: str) -> str:
    resp = client().messages.create(
        model=settings.anthropic_model,
        max_tokens=2048,
        system=(
            "너는 프로젝트 위키 검색 어시스턴트다. 제공된 근거(자료)만 사용해 한국어로 간결히 답하라.\n"
            "각 프로젝트 위키는 단일 문서이며, 변경/추가된 사실에는 본문에 `(YYYY-MM-DD 수정/추가)` 표기가 붙어 있다. "
            "이 날짜 표기를 활용해 최신 상태를 우선하고, 과거와 달라졌으면 '이전에는 X였으나 현재는 Y' 식으로 변화를 설명하라.\n"
            "근거에 없는 내용은 추측하지 말고 모른다고 답하라. 인용은 [#문서ID] 형식으로 표시하라."
        ),
        messages=[{"role": "user", "content": f"질문: {query}\n\n근거 자료:\n{context}"}],
    )
    return "".join(b.text for b in resp.content if b.type == "text").strip()
