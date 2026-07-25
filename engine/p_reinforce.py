"""
P-Reinforce ??ë©”ì¸ RL ë¶„ë¥˜ ?”ì§„
raw/ ?´ë”???Œì¼???½ì–´ ë¶„ë¥˜?˜ê³ , ?„í‚¤ ë¬¸ì„œë¥??ì„±?˜ë©°, GitHub???™ê¸°?”í•©?ˆë‹¤.

?¬ìš©ë²?
    python engine/p_reinforce.py <raw_file_path>
    python engine/p_reinforce.py --scan          # 00_Raw/ ?„ì²´ ?¤ìº”
    python engine/p_reinforce.py --status        # ?„ì¬ ?íƒœ ì¶œë ¥
    python engine/p_reinforce.py --feedback "ë¬¸ì„œëª? "ì¹?°¬|?´ë™:ì¹´í…Œê³ ë¦¬"
"""
import sys
import json
import re
from datetime import datetime
from pathlib import Path

# ?„ë¡œ?íŠ¸ ë£¨íŠ¸
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "engine"))

from wiki_template import create_wiki_document, save_wiki_document
from graph_manager import add_node, add_edge, get_related_nodes, update_index
from git_sync import sync, get_status, get_log


# ?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€
# RL ?•ì±… ë¡œë”
# ?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€
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
    # Policy.md?ì„œ ê°€ì¤‘ì¹˜ ?Œì‹±
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


# ?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€
# ë¶„ë¥˜ê¸?(Categorizer)
# ?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€
CATEGORY_KEYWORDS = {
    "Projects": [
        "?„ë¡œ?íŠ¸", "project", "ê°œë°œ", "ì¶œì‹œ", "ë§ˆê°", "?¤í”„ë¦°íŠ¸", "ëª©í‘œ", "ê³„íš",
        "deliverable", "milestone", "roadmap", "release", "deploy"
    ],
    "Topics": [
        "ê°œë…", "?´ë¡ ", "?ë¦¬", "?°êµ¬", "?™ìŠµ", "?•ì˜", "?´í•´", "ì² í•™", "?¬ë¦¬",
        "concept", "theory", "principle", "research", "study", "definition",
        "algorithm", "architecture", "model", "framework"
    ],
    "Decisions": [
        "ê²°ì •", "? íƒ", "??, "ë¹„êµ", "?¸ë ˆ?´ë“œ?¤í”„", "?Œê³ ", "?ë‹¨", "ê³ ë?",
        "decision", "tradeoff", "vs", "versus", "why", "reason", "retrospective",
        "because", "?°ë¼??, "ê·¸ëŸ¬ë¯€ë¡?
    ],
    "Skills": [
        "ë°©ë²•", "?¨ê³„", "?„ë¡¬?„íŠ¸", "?Œí¬?Œë¡œ??, "?ë™??, "?¨í„´", "ê¸°ìˆ ", "?¤í‚¬",
        "how to", "workflow", "prompt", "automation", "template", "script",
        "guide", "tutorial", "step", "process", "ë°©ë²•ë¡?
    ],
}

CATEGORY_DISPLAY = {
    "Projects": "?› ï¸?Projects",
    "Topics": "?’¡ Topics",
    "Decisions": "?–ï¸ Decisions",
    "Skills": "?? Skills",
}


def classify(text: str, policy: dict) -> tuple[str, float]:
    """?ìŠ¤?¸ë? ë¶„ë¥˜?˜ê³  (ì¹´í…Œê³ ë¦¬, ?•ì‹ ??ë¥?ë°˜í™˜?©ë‹ˆ??"""
    text_lower = text.lower()
    scores = {}
    
    for category, keywords in CATEGORY_KEYWORDS.items():
        score = 0
        for kw in keywords:
            if kw in text_lower:
                score += 1
        # ?•ì±… ê°€ì¤‘ì¹˜ ë³´ì • ?ìš©
        bonus = policy["category_weights"].get(category, 0.0)
        scores[category] = score + bonus
    
    if not any(scores.values()):
        # ê¸°ë³¸ê°? Topics
        return "Topics", 0.5
    
    best = max(scores, key=scores.get)
    total = sum(scores.values()) or 1
    confidence = scores[best] / total
    confidence = max(0.5, min(1.0, confidence))  # 0.5 ~ 1.0 ë²”ì£¼ ê³ ì •
    
    return best, confidence


def extract_title(text: str, filename: str) -> str:
    """ë§ˆí¬?¤ìš´ ?œëª© ?ëŠ” ì²?ì¤„ì—???œëª©??ì¶”ì¶œ?©ë‹ˆ??"""
    for line in text.splitlines():
        # BOM(\ufeff) ë°??ë’¤ ê³µë°± ?œê±°
        line = line.strip().lstrip('\ufeff').strip()
        if line.startswith("# "):
            return line[2:].strip()
        if line and not line.startswith("---"):
            return line[:80].lstrip('\ufeff').strip()
    return Path(filename).stem


def extract_summary(text: str) -> str:
    """?ìŠ¤?¸ì—???µì‹¬ ??ë¬¸ì¥??ì¶”ì¶œ?©ë‹ˆ??"""
    lines = [l.strip() for l in text.splitlines() if l.strip() and not l.startswith("#")]
    if lines:
        return lines[0][:200]
    return "?”ì•½ ?†ìŒ"


def extract_tags(text: str) -> list[str]:
    """?ìŠ¤?¸ì—???œê·¸ë¥?ì¶”ì¶œ?©ë‹ˆ??(?œê? ?¤ì›Œ??+ ?ì–´ ?¨ì–´)."""
    # #?œê·¸ ?¨í„´
    hashtags = re.findall(r"#(\w+)", text)
    # ë°˜ë³µ ?±ì¥ ?¤ì›Œ??(ê°„ë‹¨ êµ¬í˜„)
    all_keywords = []
    for kws in CATEGORY_KEYWORDS.values():
        for kw in kws:
            if kw in text.lower() and len(kw) > 2:
                all_keywords.append(kw)
    
    tags = list(dict.fromkeys(hashtags + all_keywords[:5]))  # ì¤‘ë³µ ?œê±°, ìµœë? 5ê°?    return tags[:8]


# ?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€
# ?´ë” ?¬ê¸° ì²´í¬ (ë¦¬íŒ©? ë§ ?¸ë¦¬ê±?
# ?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€
def check_refactor_needed(category: str, policy: dict) -> bool:
    """?´ë”???Œì¼ ?˜ê? ?„ê³„ê°’ì„ ì´ˆê³¼?˜ë©´ Trueë¥?ë°˜í™˜?©ë‹ˆ??"""
    folder = ROOT / "10_Wiki" / CATEGORY_DISPLAY[category]
    if not folder.exists():
        return False
    count = len(list(folder.glob("*.md")))
    threshold = policy.get("refactor_threshold", 12)
    if count >= threshold:
        print(f"\n? ï¸  [{category}] ?´ë”??{count}ê°??Œì¼ ({threshold}ê°?ì´ˆê³¼)")
        print(f"   ???˜ìœ„ ì¹´í…Œê³ ë¦¬ë¡??¸ë¶„??Refactoring)ë¥?ê¶Œì¥?©ë‹ˆ??")
        return True
    return False


# ?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€
# ë©”ì¸ ì²˜ë¦¬ ?Œì´?„ë¼??# ?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€
def process_raw_file(raw_path: Path) -> bool:
    """?¨ì¼ raw ?Œì¼??ì²˜ë¦¬?©ë‹ˆ??"""
    if not raw_path.exists():
        print(f"???Œì¼ ?†ìŒ: {raw_path}")
        return False
    
    print(f"\n{'='*60}")
    print(f"?“¥ ì²˜ë¦¬ ?œì‘: {raw_path.name}")
    print(f"{'='*60}")
    
    text = raw_path.read_text(encoding="utf-8", errors="replace")
    policy = load_policy()
    
    # 1. ë¶„ë¥˜
    category, confidence = classify(text, policy)
    display_cat = CATEGORY_DISPLAY[category]
    print(f"?“‚ ë¶„ë¥˜ ê²°ê³¼: [{display_cat}] (?•ì‹ ?? {confidence:.0%})")
    
    # 2. ë©”í??°ì´??ì¶”ì¶œ
    title = extract_title(text, raw_path.name)
    summary = extract_summary(text)
    tags = extract_tags(text)
    
    # 3. ê´€??ë¬¸ì„œ ì°¾ê¸°
    related = get_related_nodes(title, top_k=2)
    
    # 4. ë¦¬íŒ©? ë§ ?„ìš” ?¬ë? ì²´í¬
    check_refactor_needed(category, policy)
    
    # 5. ?„í‚¤ ë¬¸ì„œ ?ì„±
    doc_content = create_wiki_document(
        title=title,
        category_path=f"{display_cat}",
        parent_category=display_cat,
        summary=summary,
        pattern=f"{category} ?„ë©”?¸ì˜ ì§€???¨í„´",
        details=[line.strip() for line in text.splitlines() if line.strip()][:5],
        tags=tags,
        related=related,
        raw_filename=raw_path.name,
        confidence=confidence,
    )
    
    # 6. ?€??    safe_title = re.sub(r'[<>:"/\\|?*]', "_", title)[:50]
    output_path = ROOT / "10_Wiki" / display_cat / f"{safe_title}.md"
    saved = save_wiki_document(doc_content, output_path)
    
    # 7. Graph ?…ë°?´íŠ¸
    import uuid
    doc_id = str(uuid.uuid4())
    add_node(doc_id, title, category, tags, confidence)
    
    for related_title in related:
        print(f"?”— ?°ê²°: [[{title}]] ??[[{related_title}]]")
    
    # 8. Index ?…ë°?´íŠ¸
    update_index(ROOT)
    
    # 9. GitHub ?™ê¸°??    action_summary = f'"{display_cat}" ?´ë”??"{title}" ë¬¸ì„œ ì¶”ê? (?•ì‹ ??{confidence:.0%})'
    ok, commit_hash = sync(action_summary, branch="main")
    
    if ok and commit_hash not in ("no-changes", ""):
        # ì»¤ë°‹ ?´ì‹œë¥?ë¬¸ì„œ??ë°˜ì˜
        content = saved.read_text(encoding="utf-8")
        content = content.replace('"pending"', f'"{commit_hash}"')
        saved.write_text(content, encoding="utf-8")
        print(f"?“ ì»¤ë°‹ ?´ì‹œ ë°˜ì˜: {commit_hash}")
    
    print(f"\n???„ë£Œ! [{display_cat}] ??{saved.name}")
    return ok


def scan_raw_folder() -> None:
    """00_Raw/ ?´ë”??ë¯¸ì²˜ë¦??Œì¼??ëª¨ë‘ ì²˜ë¦¬?©ë‹ˆ??"""
    raw_root = ROOT / "00_Raw"
    md_files = list(raw_root.rglob("*.md")) + list(raw_root.rglob("*.txt"))
    
    # ? ì§œ ?´ë” ??.gitkeep ?œì™¸
    md_files = [f for f in md_files if f.name != ".gitkeep"]
    
    if not md_files:
        print("?“­ 00_Raw/ ?´ë”??ì²˜ë¦¬???Œì¼???†ìŠµ?ˆë‹¤.")
        return
    
    print(f"?” {len(md_files)}ê°??Œì¼ ë°œê²¬")
    for f in md_files:
        process_raw_file(f)


def show_status() -> None:
    """?„ì¬ ?„í‚¤ ?íƒœë¥?ì¶œë ¥?©ë‹ˆ??"""
    print("\n" + "="*60)
    print("?“Š P-Reinforce ?„í‚¤ ?„í™©")
    print("="*60)
    
    graph_path = ROOT / "20_Meta" / "Graph.json"
    if graph_path.exists():
        with open(graph_path, encoding="utf-8") as f:
            graph = json.load(f)
        print(f"ì´?ë¬¸ì„œ: {graph.get('total_nodes', 0)}ê°?)
        for cat, data in graph.get("categories", {}).items():
            print(f"  {cat}: {data.get('count', 0)}ê°?)
    
    print(f"\nGit ?íƒœ: {get_status() or 'clean'}")
    print("\nìµœê·¼ ì»¤ë°‹:")
    print(get_log(3) or "?†ìŒ")


def apply_feedback(doc_title: str, feedback: str) -> None:
    """
    ?¬ìš©???¼ë“œë°±ì„ Policy.md??ê¸°ë¡?©ë‹ˆ??
    feedback ?•ì‹: "ì¹?°¬" | "?´ë™:?ˆì¹´?Œê³ ë¦? | "?˜ì •:?´ìš©"
    """
    policy_path = ROOT / "20_Meta" / "Policy.md"
    today = datetime.now().strftime("%Y-%m-%d")
    
    if feedback == "ì¹?°¬":
        action, result, change = "ì¹?°¬", "??, "ë¶„ë¥˜ ê°€ì¤‘ì¹˜ +0.1"
    elif feedback.startswith("?´ë™:"):
        new_cat = feedback.split(":", 1)[1]
        action, result, change = f"?´ë™ ??{new_cat}", "?”„", f"ê²½ê³„ ?¬ì„¤??
    else:
        action, result, change = feedback, "?“", "ê¸°ë¡??
    
    log_row = f"| {today} | {doc_title} | {action} | {result} | {change} |"
    
    content = policy_path.read_text(encoding="utf-8")
    # ?¼ë“œë°?ë¡œê·¸ ?Œì´ë¸??„ë˜???½ì…
    insert_marker = "| 2026-07-25 | - | ?œìŠ¤??ì´ˆê¸°??
    new_content = content.replace(insert_marker, f"{log_row}\n{insert_marker}")
    policy_path.write_text(new_content, encoding="utf-8")
    
    print(f"???¼ë“œë°?ê¸°ë¡?? {doc_title} ??{action}")
    sync(f"?¼ë“œë°?ë°˜ì˜: {doc_title} ({action})")


# ?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€
# CLI ì§„ì…??# ?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€?€
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
