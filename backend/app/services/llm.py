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
            "meta": {
                "type": "array",
                "description": (
                    "프로젝트 핵심 정보/거버넌스. 위키 상단에 표시됨. "
                    "기본 항목은 이 프로젝트에 해당하면 '웬만하면 항상' 포함한다: 고객사, 사업기간, 사업규모, 상태/단계, 담당(PM/팀), 핵심목표. "
                    "이 기본 항목의 값을 알 수 없으면 항목을 빼지 말고 value 를 '미상' 으로 적는다(빈 문자열 금지). "
                    "그 외 프로젝트에 의미 있는 항목(계약형태, 인력규모 등)은 값이 있을 때만 추가한다. "
                    "기존 meta 값은 보존하되 새 정보로 갱신한다(이전에 '미상'이던 값이 확인되면 갱신)."
                ),
                "items": {
                    "type": "object",
                    "properties": {
                        "label": {"type": "string"},
                        "value": {"type": "string"},
                    },
                    "required": ["label", "value"],
                },
            },
            "content_md": {
                "type": "string",
                "description": (
                    "프로젝트 위키 '진행 내용' 본문(마크다운). 메타(고객사/기간/규모 등)는 여기 중복하지 말 것(meta 필드에). "
                    "진행 내용을 카테고리별로 `## 카테고리명` 섹션으로 묶고, 각 섹션 안에서는 '시간순(오래된→최신)'으로 정렬한다. "
                    "각 항목 끝에 가능한 날짜(`(M/D)` 또는 `(YYYY-MM-DD)`)를 붙이고, 이번에 변경/추가된 항목에는 `(YYYY-MM-DD 수정)`·`(YYYY-MM-DD 추가)` 표기를 붙인다. "
                    "기존 내용은 보존하되 같은 항목이 갱신되면 최신으로 바꾼다. 별도 변경이력 섹션은 만들지 않는다. "
                    "명백한 OCR/오타는 교정하되 숫자·날짜·금액·고유명사 값은 보존한다."
                ),
            },
            "categories": {
                "type": "array",
                "description": (
                    "content_md 에서 사용한 카테고리(분류) 목록. 표준 후보: 영업/계약, 기획/설계, 개발, 테스트/QA, 보고/커뮤니케이션, 운영/오픈, 이슈/리스크, 기타. "
                    "적합하면 표준을 쓰고, 필요하면 프로젝트에 맞는 카테고리를 추가한다."
                ),
                "items": {"type": "string"},
            },
            "rename_to": {
                "type": "string",
                "description": "사용자가 '프로젝트 이름/제목 자체'를 변경·교정하라고 명시적으로 지시했을 때만 새 프로젝트 이름을 넣는다(예: '오상공장을 오산공장으로 고쳐줘'). 그 외에는 빈 문자열.",
            },
            "clarifications": {
                "type": "array",
                "description": (
                    "OCR 깨짐/오타로 의미를 확신할 수 없어 '사용자 확인이 필요한' 부분만 나열한다. "
                    "확실히 이해되는 내용은 절대 넣지 마라. 주로 깨진 고유명사·숫자·약어. 없으면 빈 배열."
                ),
                "items": {
                    "type": "object",
                    "properties": {
                        "context": {"type": "string", "description": "문제가 된 원문 조각(깨진 표현 포함)"},
                        "question": {"type": "string", "description": "무엇이 맞는지 사용자에게 물을 질문"},
                    },
                    "required": ["context", "question"],
                },
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
        "required": ["project_name", "meta", "content_md", "categories", "change_summary", "entities", "relations"],
    },
}


def merge(existing_md: str, new_text: str, known_projects: list[str], today: str,
          hinted_project: str | None, existing_meta: list | None = None) -> dict:
    hint = f"\n사용자가 지정한 프로젝트: {hinted_project} (이 프로젝트로 귀속)." if hinted_project else ""
    known = ", ".join(known_projects) if known_projects else "(없음)"
    existing_block = existing_md.strip() or "(아직 위키 없음 — 새로 작성)"
    meta_block = json.dumps(existing_meta, ensure_ascii=False) if existing_meta else "(없음)"
    resp = client().messages.create(
        model=settings.anthropic_model,
        max_tokens=8192,
        tools=[MERGE_TOOL],
        tool_choice={"type": "tool", "name": "update_project_wiki"},
        messages=[{
            "role": "user",
            "content": (
                f"오늘 날짜: {today}\n알려진 프로젝트: {known}{hint}\n\n"
                f"=== 기존 프로젝트 메타 ===\n{meta_block}\n\n"
                f"=== 기존 위키 진행내용 본문 ===\n{existing_block}\n\n"
                f"=== 새로 들어온 입력 ===\n{new_text}\n\n"
                "위 새 입력을 기존 위키에 병합해 '전체 갱신본'을 만든다. "
                "프로젝트 핵심정보는 meta 로, 진행내용은 카테고리별·시간순으로 content_md 에 정리하고, 사용한 카테고리 목록과 변경 요약, 온톨로지를 추출하라."
            ),
        }],
    )
    for block in resp.content:
        if block.type == "tool_use" and block.name == "update_project_wiki":
            return block.input
    raise RuntimeError("위키 병합 실패")


ANALYZE_TOOL = {
    "name": "analyze_wiki",
    "description": "주어진 위키 본문에서 카테고리 분류와 온톨로지(엔티티/관계)를 추출한다. 본문은 수정하지 않는다.",
    "input_schema": {
        "type": "object",
        "properties": {
            "categories": {"type": "array", "items": {"type": "string"},
                           "description": "본문 섹션의 카테고리 분류 목록 (영업/계약, 개발, 테스트/QA 등)."},
            "entities": {
                "type": "array",
                "items": {"type": "object", "properties": {
                    "name": {"type": "string"}, "type": {"type": "string"}}, "required": ["name", "type"]},
            },
            "relations": {
                "type": "array",
                "items": {"type": "object", "properties": {
                    "subject": {"type": "string"}, "predicate": {"type": "string"}, "object": {"type": "string"}},
                    "required": ["subject", "predicate", "object"]},
            },
            "clarifications": {
                "type": "array",
                "description": "OCR 깨짐/오타로 의미가 불확실해 사용자 확인이 필요한 부분만. 확실한 건 제외. 없으면 빈 배열.",
                "items": {"type": "object", "properties": {
                    "context": {"type": "string"}, "question": {"type": "string"}},
                    "required": ["context", "question"]},
            },
        },
        "required": ["categories", "entities", "relations"],
    },
}


def analyze(content_md: str) -> dict:
    """수동 편집된 본문에서 카테고리/온톨로지만 재추출 (본문 자체는 건드리지 않음)."""
    resp = client().messages.create(
        model=settings.anthropic_model,
        max_tokens=4096,
        tools=[ANALYZE_TOOL],
        tool_choice={"type": "tool", "name": "analyze_wiki"},
        messages=[{"role": "user", "content": f"다음 위키 본문에서 카테고리와 온톨로지를 추출하라:\n\n{content_md}"}],
    )
    for block in resp.content:
        if block.type == "tool_use" and block.name == "analyze_wiki":
            return block.input
    return {"categories": [], "entities": [], "relations": []}


ROUTE_TOOL = {
    "name": "route_to_projects",
    "description": "입력 내용을 프로젝트(회사/클라이언트/사업 건 단위)별로 분리한다.",
    "input_schema": {
        "type": "object",
        "properties": {
            "segments": {
                "type": "array",
                "description": "프로젝트별로 분리된 조각들. 서로 다른 회사/클라이언트/건은 각각 별도 segment.",
                "items": {
                    "type": "object",
                    "properties": {
                        "project_name": {
                            "type": "string",
                            "description": "이 조각이 속한 프로젝트 이름. 기존 목록에 명확히 해당하면 그 이름을 '정확히' 그대로, 아니면 구체적인 새 이름(회사/클라이언트명 등).",
                        },
                        "content": {
                            "type": "string",
                            "description": "이 프로젝트에 해당하는 입력 내용. 원문에서 해당 부분을 추려 의미를 보존해 담는다.",
                        },
                    },
                    "required": ["project_name", "content"],
                },
            },
        },
        "required": ["segments"],
    },
}


def route(text: str, known_projects: list[str], today: str, max_tokens: int = 8192) -> list[dict]:
    """입력을 프로젝트(회사/클라이언트/건)별 segment 로 분리. 서로 다른 주제는 절대 한 프로젝트로 안 묶는다."""
    known = ", ".join(known_projects) if known_projects else "(없음)"
    resp = client().messages.create(
        model=settings.anthropic_model,
        max_tokens=max_tokens,
        tools=[ROUTE_TOOL],
        tool_choice={"type": "tool", "name": "route_to_projects"},
        system=(
            "너는 입력 내용을 '프로젝트' 단위로 분류·분리한다. 프로젝트는 서로 다른 회사·클라이언트·사업 건을 뜻한다 "
            "(예: 신한은행, SK온, SK가스, CSWind 는 각각 별개 프로젝트).\n"
            "규칙:\n"
            "1) 서로 다른 회사/클라이언트/건은 절대 한 프로젝트로 묶지 말고 각각 별도 segment 로 분리한다.\n"
            "2) 같은 주제(같은 회사/건)의 내용은 하나의 segment 로 묶는다(과도 분할 금지).\n"
            "3) 기존 프로젝트 목록에 명확히 해당하면 그 이름을 '정확히' 재사용한다. 아니면 구체적인 새 이름(회사/클라이언트명)을 쓴다.\n"
            "4) 'inc', '기타', '일반', '회사', '프로젝트' 같은 모호한 포괄 이름은 절대 만들지 않는다.\n"
            "5) 모회사 우산 아래라도 외부 클라이언트나 독립 계약 건은 별도 프로젝트로 분리한다."
        ),
        messages=[{
            "role": "user",
            "content": f"오늘 날짜: {today}\n기존 프로젝트: {known}\n\n=== 입력 ===\n{text}",
        }],
    )
    for block in resp.content:
        if block.type == "tool_use" and block.name == "route_to_projects":
            segs = block.input.get("segments") or []
            return [s for s in segs if (s.get("content") or "").strip()]
    return [{"project_name": "Untitled", "content": text}]


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
