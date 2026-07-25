"""
P-Reinforce Engine — Graph Manager
지식 간 연결 관계를 Graph.json에 저장/업데이트합니다.
"""
import json
from datetime import datetime
from pathlib import Path

GRAPH_PATH = Path(__file__).parent.parent / "20_Meta" / "Graph.json"


def load_graph() -> dict:
    """Graph.json을 로드합니다."""
    if GRAPH_PATH.exists():
        with open(GRAPH_PATH, encoding="utf-8") as f:
            return json.load(f)
    return {"version": "1.0.0", "nodes": [], "edges": [], "categories": {}}


def save_graph(graph: dict) -> None:
    """Graph.json을 저장합니다."""
    graph["last_updated"] = datetime.now().strftime("%Y-%m-%d")
    with open(GRAPH_PATH, "w", encoding="utf-8") as f:
        json.dump(graph, f, ensure_ascii=False, indent=2)
    print(f"✅ Graph.json 업데이트: {graph['total_nodes']}개 노드")


def add_node(doc_id: str, title: str, category: str, tags: list[str], confidence: float) -> None:
    """새 문서 노드를 그래프에 추가합니다."""
    graph = load_graph()
    
    # 중복 체크
    existing_ids = {n["id"] for n in graph.get("nodes", [])}
    if doc_id in existing_ids:
        print(f"⚠️ 노드 이미 존재: {doc_id}")
        return

    node = {
        "id": doc_id,
        "title": title,
        "category": category,
        "tags": tags,
        "confidence": confidence,
        "created_at": datetime.now().isoformat(),
    }
    graph.setdefault("nodes", []).append(node)
    graph["total_nodes"] = len(graph["nodes"])

    # 카테고리 카운트 업데이트
    cat_key = category.split("/")[-1] if "/" in category else category
    graph.setdefault("categories", {})
    if cat_key not in graph["categories"]:
        graph["categories"][cat_key] = {"count": 0}
    graph["categories"][cat_key]["count"] += 1

    save_graph(graph)


def add_edge(source_id: str, target_id: str, relation: str = "related") -> None:
    """두 노드 사이의 연결을 그래프에 추가합니다."""
    graph = load_graph()
    
    edge = {
        "source": source_id,
        "target": target_id,
        "relation": relation,
        "created_at": datetime.now().isoformat(),
    }
    graph.setdefault("edges", []).append(edge)
    save_graph(graph)


def get_related_nodes(title: str, top_k: int = 3) -> list[str]:
    """제목 키워드 기반으로 관련 문서를 찾습니다 (단순 키워드 매칭)."""
    graph = load_graph()
    title_words = set(title.lower().split())
    
    scored = []
    for node in graph.get("nodes", []):
        node_words = set(node["title"].lower().split())
        overlap = len(title_words & node_words)
        if overlap > 0:
            scored.append((overlap, node["title"]))
    
    scored.sort(reverse=True)
    return [t for _, t in scored[:top_k]]


def update_index(wiki_root: Path) -> None:
    """20_Meta/Index.md의 문서 수 통계를 업데이트합니다."""
    graph = load_graph()
    categories = graph.get("categories", {})
    
    index_path = wiki_root / "20_Meta" / "Index.md"
    if not index_path.exists():
        return

    content = index_path.read_text(encoding="utf-8")
    
    # 카테고리별 카운트 교체
    cat_map = {
        "🛠️ Projects": categories.get("Projects", {}).get("count", 0),
        "💡 Topics": categories.get("Topics", {}).get("count", 0),
        "⚖️ Decisions": categories.get("Decisions", {}).get("count", 0),
        "🚀 Skills": categories.get("Skills", {}).get("count", 0),
    }
    total = sum(cat_map.values())

    # 간단한 테이블 재생성
    table_lines = ["| 카테고리 | 문서 수 | 마지막 업데이트 |",
                   "|---|---|---|"]
    today = datetime.now().strftime("%Y-%m-%d")
    for cat, count in cat_map.items():
        table_lines.append(f"| {cat} | {count} | {today} |")
    table_lines.append(f"| **합계** | **{total}** | **{today}** |")
    
    # 테이블 섹션 교체 (단순 교체)
    new_table = "\n".join(table_lines)
    # 기존 테이블 블록 찾아 교체
    import re
    pattern = r"(\| 카테고리.*?\| \*\*합계\*\*.*?\|)"
    updated = re.sub(pattern, new_table, content, flags=re.DOTALL)
    index_path.write_text(updated, encoding="utf-8")
    print(f"✅ Index.md 업데이트 완료 (총 {total}개 문서)")
