"""
P-Reinforce — 메인 RL 분류 엔진
raw/ 폴더의 파일을 읽어 분류하고, 위키 문서를 생성하며, GitHub에 동기화합니다.

사용법:
    python engine/p_reinforce.py <raw_file_path>
    python engine/p_reinforce.py --scan          # 00_Raw/ 전체 스캔
    python engine/p_reinforce.py --status        # 현재 상태 출력
    python engine/p_reinforce.py --feedback "문서명" "칭찬|이동:카테고리"
"""
import sys
import json
import re
from datetime import datetime
from pathlib import Path

# 프로젝트 루트
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "engine"))

from wiki_template import create_wiki_document, save_wiki_document
from graph_manager import add_node, add_edge, get_related_nodes, update_index
from git_sync import sync, get_status, get_log


# ─────────────────────────────────────────────
# RL 정책 로더
# ─────────────────────────────────────────────
def load_policy() -> dict:
    policy_path = ROOT / "20_Meta" / "Policy.md"
    policy = {
        "w1": 0.5, "w2": 0.3, "w3": 0.2,
        "similarity_threshold": 0.85,
        "refactor_threshold": 12,
        "category_weights": {
            "Projects": 0.0,
            "Topics": 0.0,
            "Decisions": 0.0,
            "Skills": 0.0,
        }
    }
    # Policy.md에서 가중치 파싱
    if policy_path.exists():
        text = policy_path.read_text(encoding="utf-8")
        for key, pattern in [
            ("w1", r"`w1_categorization`\s*\|\s*([\d.]+)"),
            ("w2", r"`w2_connectivity`\s*\|\s*([\d.]+)"),
            ("w3", r"`w3_user_satisfaction`\s*\|\s*([\d.]+)"),
        ]:
            m = re.search(pattern, text)
            if m:
                policy[key] = float(m.group(1))
    return policy


# ─────────────────────────────────────────────
# 분류기 (Categorizer)
# ─────────────────────────────────────────────
CATEGORY_KEYWORDS = {
    "Projects": [
        "프로젝트", "project", "개발", "출시", "마감", "스프린트", "목표", "계획",
        "deliverable", "milestone", "roadmap", "release", "deploy"
    ],
    "Topics": [
        "개념", "이론", "원리", "연구", "학습", "정의", "이해", "철학", "심리",
        "concept", "theory", "principle", "research", "study", "definition",
        "algorithm", "architecture", "model", "framework"
    ],
    "Decisions": [
        "결정", "선택", "왜", "비교", "트레이드오프", "회고", "판단", "고민",
        "decision", "tradeoff", "vs", "versus", "why", "reason", "retrospective",
        "because", "따라서", "그러므로"
    ],
    "Skills": [
        "방법", "단계", "프롬프트", "워크플로우", "자동화", "패턴", "기술", "스킬",
        "how to", "workflow", "prompt", "automation", "template", "script",
        "guide", "tutorial", "step", "process", "방법론"
    ],
}

CATEGORY_DISPLAY = {
    "Projects": "🛠️ Projects",
    "Topics": "💡 Topics",
    "Decisions": "⚖️ Decisions",
    "Skills": "🚀 Skills",
}


def classify(text: str, policy: dict) -> tuple[str, float]:
    """텍스트를 분류하고 (카테고리, 확신도)를 반환합니다."""
    text_lower = text.lower()
    scores = {}
    
    for category, keywords in CATEGORY_KEYWORDS.items():
        score = 0
        for kw in keywords:
            if kw in text_lower:
                score += 1
        # 정책 가중치 보정 적용
        bonus = policy["category_weights"].get(category, 0.0)
        scores[category] = score + bonus
    
    if not any(scores.values()):
        # 기본값: Topics
        return "Topics", 0.5
    
    best = max(scores, key=scores.get)
    total = sum(scores.values()) or 1
    confidence = scores[best] / total
    confidence = max(0.5, min(1.0, confidence))  # 0.5 ~ 1.0 범주 고정
    
    return best, confidence


def extract_title(text: str, filename: str) -> str:
    """마크다운 제목 또는 첫 줄에서 제목을 추출합니다."""
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("# "):
            return line[2:].strip()
        if line and not line.startswith("---"):
            return line[:80]
    return Path(filename).stem


def extract_summary(text: str) -> str:
    """텍스트에서 핵심 한 문장을 추출합니다."""
    lines = [l.strip() for l in text.splitlines() if l.strip() and not l.startswith("#")]
    if lines:
        return lines[0][:200]
    return "요약 없음"


def extract_tags(text: str) -> list[str]:
    """텍스트에서 태그를 추출합니다 (한글 키워드 + 영어 단어)."""
    # #태그 패턴
    hashtags = re.findall(r"#(\w+)", text)
    # 반복 등장 키워드 (간단 구현)
    all_keywords = []
    for kws in CATEGORY_KEYWORDS.values():
        for kw in kws:
            if kw in text.lower() and len(kw) > 2:
                all_keywords.append(kw)
    
    tags = list(dict.fromkeys(hashtags + all_keywords[:5]))  # 중복 제거, 최대 5개
    return tags[:8]


# ─────────────────────────────────────────────
# 폴더 크기 체크 (리팩토링 트리거)
# ─────────────────────────────────────────────
def check_refactor_needed(category: str, policy: dict) -> bool:
    """폴더의 파일 수가 임계값을 초과하면 True를 반환합니다."""
    folder = ROOT / "10_Wiki" / CATEGORY_DISPLAY[category]
    if not folder.exists():
        return False
    count = len(list(folder.glob("*.md")))
    threshold = policy.get("refactor_threshold", 12)
    if count >= threshold:
        print(f"\n⚠️  [{category}] 폴더에 {count}개 파일 ({threshold}개 초과)")
        print(f"   → 하위 카테고리로 세분화(Refactoring)를 권장합니다.")
        return True
    return False


# ─────────────────────────────────────────────
# 메인 처리 파이프라인
# ─────────────────────────────────────────────
def process_raw_file(raw_path: Path) -> bool:
    """단일 raw 파일을 처리합니다."""
    if not raw_path.exists():
        print(f"❌ 파일 없음: {raw_path}")
        return False
    
    print(f"\n{'='*60}")
    print(f"📥 처리 시작: {raw_path.name}")
    print(f"{'='*60}")
    
    text = raw_path.read_text(encoding="utf-8", errors="replace")
    policy = load_policy()
    
    # 1. 분류
    category, confidence = classify(text, policy)
    display_cat = CATEGORY_DISPLAY[category]
    print(f"📂 분류 결과: [{display_cat}] (확신도: {confidence:.0%})")
    
    # 2. 메타데이터 추출
    title = extract_title(text, raw_path.name)
    summary = extract_summary(text)
    tags = extract_tags(text)
    
    # 3. 관련 문서 찾기
    related = get_related_nodes(title, top_k=2)
    
    # 4. 리팩토링 필요 여부 체크
    check_refactor_needed(category, policy)
    
    # 5. 위키 문서 생성
    doc_content = create_wiki_document(
        title=title,
        category_path=f"{display_cat}",
        parent_category=display_cat,
        summary=summary,
        pattern=f"{category} 도메인의 지식 패턴",
        details=[line.strip() for line in text.splitlines() if line.strip()][:5],
        tags=tags,
        related=related,
        raw_filename=raw_path.name,
        confidence=confidence,
    )
    
    # 6. 저장
    safe_title = re.sub(r'[<>:"/\\|?*]', "_", title)[:50]
    output_path = ROOT / "10_Wiki" / display_cat / f"{safe_title}.md"
    saved = save_wiki_document(doc_content, output_path)
    
    # 7. Graph 업데이트
    import uuid
    doc_id = str(uuid.uuid4())
    add_node(doc_id, title, category, tags, confidence)
    
    for related_title in related:
        print(f"🔗 연결: [[{title}]] ↔ [[{related_title}]]")
    
    # 8. Index 업데이트
    update_index(ROOT)
    
    # 9. GitHub 동기화
    action_summary = f'"{display_cat}" 폴더에 "{title}" 문서 추가 (확신도 {confidence:.0%})'
    ok, commit_hash = sync(action_summary)
    
    if ok and commit_hash not in ("no-changes", ""):
        # 커밋 해시를 문서에 반영
        content = saved.read_text(encoding="utf-8")
        content = content.replace('"pending"', f'"{commit_hash}"')
        saved.write_text(content, encoding="utf-8")
        print(f"📝 커밋 해시 반영: {commit_hash}")
    
    print(f"\n✨ 완료! [{display_cat}] → {saved.name}")
    return ok


def scan_raw_folder() -> None:
    """00_Raw/ 폴더의 미처리 파일을 모두 처리합니다."""
    raw_root = ROOT / "00_Raw"
    md_files = list(raw_root.rglob("*.md")) + list(raw_root.rglob("*.txt"))
    
    # 날짜 폴더 내 .gitkeep 제외
    md_files = [f for f in md_files if f.name != ".gitkeep"]
    
    if not md_files:
        print("📭 00_Raw/ 폴더에 처리할 파일이 없습니다.")
        return
    
    print(f"🔍 {len(md_files)}개 파일 발견")
    for f in md_files:
        process_raw_file(f)


def show_status() -> None:
    """현재 위키 상태를 출력합니다."""
    print("\n" + "="*60)
    print("📊 P-Reinforce 위키 현황")
    print("="*60)
    
    graph_path = ROOT / "20_Meta" / "Graph.json"
    if graph_path.exists():
        with open(graph_path, encoding="utf-8") as f:
            graph = json.load(f)
        print(f"총 문서: {graph.get('total_nodes', 0)}개")
        for cat, data in graph.get("categories", {}).items():
            print(f"  {cat}: {data.get('count', 0)}개")
    
    print(f"\nGit 상태: {get_status() or 'clean'}")
    print("\n최근 커밋:")
    print(get_log(3) or "없음")


def apply_feedback(doc_title: str, feedback: str) -> None:
    """
    사용자 피드백을 Policy.md에 기록합니다.
    feedback 형식: "칭찬" | "이동:새카테고리" | "수정:내용"
    """
    policy_path = ROOT / "20_Meta" / "Policy.md"
    today = datetime.now().strftime("%Y-%m-%d")
    
    if feedback == "칭찬":
        action, result, change = "칭찬", "✅", "분류 가중치 +0.1"
    elif feedback.startswith("이동:"):
        new_cat = feedback.split(":", 1)[1]
        action, result, change = f"이동 → {new_cat}", "🔄", f"경계 재설정"
    else:
        action, result, change = feedback, "📝", "기록됨"
    
    log_row = f"| {today} | {doc_title} | {action} | {result} | {change} |"
    
    content = policy_path.read_text(encoding="utf-8")
    # 피드백 로그 테이블 아래에 삽입
    insert_marker = "| 2026-07-25 | - | 시스템 초기화"
    new_content = content.replace(insert_marker, f"{log_row}\n{insert_marker}")
    policy_path.write_text(new_content, encoding="utf-8")
    
    print(f"✅ 피드백 기록됨: {doc_title} → {action}")
    sync(f"피드백 반영: {doc_title} ({action})")


# ─────────────────────────────────────────────
# CLI 진입점
# ─────────────────────────────────────────────
if __name__ == "__main__":
    args = sys.argv[1:]
    
    if not args or args[0] == "--help":
        print(__doc__)
        sys.exit(0)
    
    if args[0] == "--scan":
        scan_raw_folder()
    
    elif args[0] == "--status":
        show_status()
    
    elif args[0] == "--feedback" and len(args) >= 3:
        apply_feedback(args[1], args[2])
    
    else:
        raw_path = Path(args[0])
        if not raw_path.is_absolute():
            raw_path = ROOT / raw_path
        success = process_raw_file(raw_path)
        sys.exit(0 if success else 1)
