"""URL에서 외부 자료를 가져와 텍스트로 추출한다.

지원: 일반 웹페이지(본문 텍스트), Google Docs/Sheets/Slides(export), Google Drive 파일(download),
PDF/DOCX/PPTX/XLSX(기존 파서), 일반 텍스트. 회사망 SSL 인터셉트 대응으로 기본 verify=off.
"""
import re
import warnings

import httpx

from . import extract_files

warnings.filterwarnings("ignore", message="Unverified HTTPS request")

_UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36"

_GDOCS = re.compile(r"docs\.google\.com/(document|spreadsheets|presentation)/d/([a-zA-Z0-9_-]+)")
_GDRIVE = re.compile(r"drive\.google\.com/(?:file/d/|open\?id=|uc\?id=)([a-zA-Z0-9_-]+)")


def _normalize(url: str) -> str:
    """구글 문서/드라이브 공유 링크를 다운로드/export URL로 변환."""
    m = _GDOCS.search(url)
    if m:
        kind, did = m.group(1), m.group(2)
        fmt = {"document": "txt", "spreadsheets": "csv", "presentation": "pdf"}[kind]
        return f"https://docs.google.com/{kind}/d/{did}/export?format={fmt}"
    m = _GDRIVE.search(url)
    if m:
        return f"https://drive.google.com/uc?export=download&id={m.group(1)}"
    return url


def _html_to_text(data: bytes) -> str:
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(data, "html.parser")
    for t in soup(["script", "style", "noscript", "nav", "footer", "header", "aside", "iframe", "svg", "form"]):
        t.decompose()
    title = (soup.title.string or "").strip() if soup.title else ""
    text = soup.get_text("\n")
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    body = "\n".join(lines)
    return (f"# {title}\n\n{body}" if title else body).strip()


def fetch_url(url: str) -> str:
    """URL 내용을 텍스트로 추출. 실패 시 예외."""
    target = _normalize(url)
    with httpx.Client(verify=False, follow_redirects=True, timeout=30.0, headers={"User-Agent": _UA}) as c:
        r = c.get(target)
        r.raise_for_status()
        ct = (r.headers.get("content-type") or "").lower()
        data = r.content

    path = url.split("?")[0].lower()
    if "pdf" in ct or path.endswith(".pdf"):
        return extract_files._pdf(data)
    if "presentationml" in ct or path.endswith(".pptx"):
        return extract_files._pptx(data)
    if "wordprocessingml" in ct or path.endswith(".docx"):
        return extract_files._docx(data)
    if "spreadsheetml" in ct or path.endswith(".xlsx"):
        return extract_files._xlsx(data)
    if "html" in ct or "xml" in ct or ct.startswith("text/html"):
        return _html_to_text(data)
    if path.endswith((".txt", ".csv", ".md", ".json")) or "text/" in ct:
        return data.decode("utf-8", errors="replace").strip()
    # 알 수 없는 형식 → HTML 추출 시도
    return _html_to_text(data)
