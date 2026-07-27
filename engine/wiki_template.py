"""
P-Reinforce Engine — Wiki Template Generator
위키 문서 변환 규격에 따라 마크다운 파일을 생성합니다.
"""
import uuid
from datetime import datetime
from pathlib import Path


WIKI_TEMPLATE = """\
---
id: {doc_id}
category: "[[10_Wiki/{category_path}]]"
confidence_score: {confidence:.2f}
tags: [{tags}]
last_reinforced: {date}
github_commit: "{commit_hash}"
---

# [[{title}]]

## 📌 한 줄 통찰 (The Karpathy Summary)
> {summary}

## 📖 구조화된 지식 (Synthesized Content)
- **추출된 패턴:** {pattern}
- **세부 내용:**
{details}

## ⚠️ 모순 및 업데이트 (Contradictions & RL Update)
- **과거 데이터와의 충돌:** 없음 (최초 등록)
- **정책 변화:** 이 문서를 통해 강화된 분류 기준 없음 (초기 상태)

## 🔗 지식 연결 (Graph)
- **Parent:** [[10_Wiki/{parent_category}]]
- **Related:** {related}
- **Raw Source:** [[00_Raw/{raw_date}/{raw_filename}]]
"""


def generate_doc_id() -> str:
    return str(uuid.uuid4())


def format_details(details: list[str]) -> str:
    return "\n".join(f"  - {d}" for d in details) if details else "  - (내용 없음)"


def create_wiki_document(
    title: str,
    category_path: str,
    parent_category: str,
    summary: str,
    pattern: str,
    details: list[str],
    tags: list[str],
    related: list[str],
    raw_filename: str,
    confidence: float = 0.75,
    commit_hash: str = "pending",
) -> str:
    """위키 템플릿에 맞는 마크다운 문자열을 반환합니다."""
    return WIKI_TEMPLATE.format(
        doc_id=generate_doc_id(),
        category_path=category_path,
        confidence=confidence,
        tags=", ".join(tags),
        date=datetime.now().strftime("%Y-%m-%d"),
        commit_hash=commit_hash,
        title=title,
        summary=summary,
        pattern=pattern,
        details=format_details(details),
        parent_category=parent_category,
        related=", ".join(f"[[{r}]]" for r in related) if related else "없음",
        raw_date=datetime.now().strftime("%Y-%m-%d"),
        raw_filename=raw_filename,
    )


def save_wiki_document(content: str, output_path: Path) -> Path:
    """위키 문서를 파일로 저장합니다."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(content, encoding="utf-8")
    print(f"✅ 위키 문서 저장: {output_path}")
    return output_path
