"""
fetch_youtube_knowledge.py
─────────────────────────────────────────────────────────────
YouTube Data API v3를 사용해 내 채널의 모든 영상을 가져오고
Obsidian 호환 마크다운 지식 파일로 구조화합니다.

출력 구조:
  knowledge/
    index.md                  ← 전체 채널 인덱스
    videos/
      [[영상 제목]].md        ← 영상별 지식 파일
"""

import os
import re
import pickle
import json
import isodate
from datetime import datetime, timezone
from pathlib import Path

import google_auth_oauthlib.flow
import googleapiclient.discovery
from google.auth.transport.requests import Request

# ──────────────────────────────────────────────
# 설정
# ──────────────────────────────────────────────
SCOPES = [
    "https://www.googleapis.com/auth/youtube.readonly",
]
TOKEN_PATH = "token.pickle"
CLIENT_SECRETS_PATH = "client_secrets.json"
OUTPUT_DIR = Path("knowledge")
VIDEOS_DIR = OUTPUT_DIR / "videos"
TODAY = datetime.now(timezone.utc).strftime("%Y-%m-%d")

# ──────────────────────────────────────────────
# 인증
# ──────────────────────────────────────────────
def get_authenticated_service():
    """OAuth2 인증 후 YouTube API 서비스 객체 반환 (토큰 캐시 사용)."""
    creds = None

    if os.path.exists(TOKEN_PATH):
        with open(TOKEN_PATH, "rb") as f:
            creds = pickle.load(f)

    # 스코프가 변경됐거나 토큰이 유효하지 않으면 재인증
    if not creds or not creds.valid or not set(SCOPES).issubset(set(creds.scopes or [])):
        if creds and creds.expired and creds.refresh_token:
            print("🔄 만료된 자격증명 갱신 중...")
            try:
                creds.refresh(Request())
            except Exception:
                creds = None

        if not creds or not creds.valid:
            print("🔑 OAuth2 인증 플로우 시작 (브라우저가 열립니다)...")
            flow = google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file(
                CLIENT_SECRETS_PATH, SCOPES
            )
            creds = flow.run_local_server(host="localhost", port=8080)

        with open(TOKEN_PATH, "wb") as f:
            pickle.dump(creds, f)
        print("✅ 자격증명 저장 완료")

    return googleapiclient.discovery.build("youtube", "v3", credentials=creds)


# ──────────────────────────────────────────────
# 채널 정보 가져오기
# ──────────────────────────────────────────────
def get_channel_info(youtube):
    """내 채널의 기본 정보와 업로드 플레이리스트 ID를 반환."""
    resp = youtube.channels().list(
        part="snippet,contentDetails,statistics",
        mine=True
    ).execute()

    channel = resp["items"][0]
    return {
        "id": channel["id"],
        "title": channel["snippet"]["title"],
        "description": channel["snippet"].get("description", ""),
        "subscriber_count": channel["statistics"].get("subscriberCount", "비공개"),
        "video_count": channel["statistics"].get("videoCount", "0"),
        "view_count": channel["statistics"].get("viewCount", "0"),
        "uploads_playlist_id": channel["contentDetails"]["relatedPlaylists"]["uploads"],
    }


# ──────────────────────────────────────────────
# 전체 영상 ID 수집 (페이지네이션)
# ──────────────────────────────────────────────
def get_all_video_ids(youtube, playlist_id):
    """업로드 플레이리스트에서 모든 영상 ID를 수집."""
    video_ids = []
    next_page_token = None

    print("📋 영상 ID 수집 중...")
    while True:
        resp = youtube.playlistItems().list(
            part="contentDetails",
            playlistId=playlist_id,
            maxResults=50,
            pageToken=next_page_token,
        ).execute()

        for item in resp["items"]:
            video_ids.append(item["contentDetails"]["videoId"])

        next_page_token = resp.get("nextPageToken")
        if not next_page_token:
            break

    print(f"   총 {len(video_ids)}개 영상 ID 수집 완료")
    return video_ids


# ──────────────────────────────────────────────
# 영상 상세 정보 배치 수집
# ──────────────────────────────────────────────
def get_video_details(youtube, video_ids):
    """영상 ID 목록으로 상세 정보를 배치(50개씩) 수집."""
    all_videos = []
    batch_size = 50

    for i in range(0, len(video_ids), batch_size):
        batch = video_ids[i: i + batch_size]
        print(f"   영상 상세 정보 수집 중... ({i + 1}~{i + len(batch)} / {len(video_ids)})")

        resp = youtube.videos().list(
            part="snippet,statistics,contentDetails,status",
            id=",".join(batch),
        ).execute()

        all_videos.extend(resp.get("items", []))

    return all_videos


# ──────────────────────────────────────────────
# 유틸: 파일명 안전하게 변환
# ──────────────────────────────────────────────
def safe_filename(title: str) -> str:
    """Obsidian 파일명에 사용 불가한 문자를 제거/치환."""
    # Windows & Obsidian 불허 문자 제거
    title = re.sub(r'[\\/:*?"<>|#\[\]]', "", title)
    title = title.strip().strip(".")
    return title[:200] if title else "untitled"


# ──────────────────────────────────────────────
# 유틸: ISO 8601 재생시간 → 읽기 좋은 형태
# ──────────────────────────────────────────────
def format_duration(iso_duration: str) -> str:
    try:
        duration = isodate.parse_duration(iso_duration)
        total_seconds = int(duration.total_seconds())
        h = total_seconds // 3600
        m = (total_seconds % 3600) // 60
        s = total_seconds % 60
        if h > 0:
            return f"{h}:{m:02d}:{s:02d}"
        return f"{m}:{s:02d}"
    except Exception:
        return iso_duration


# ──────────────────────────────────────────────
# 유틸: 숫자 포맷 (1234567 → 1,234,567)
# ──────────────────────────────────────────────
def fmt_num(n) -> str:
    try:
        return f"{int(n):,}"
    except (TypeError, ValueError):
        return str(n)


# ──────────────────────────────────────────────
# 마크다운 생성: 영상 1개
# ──────────────────────────────────────────────
def build_video_md(video: dict, channel_title: str) -> str:
    snippet = video.get("snippet", {})
    stats = video.get("statistics", {})
    content_details = video.get("contentDetails", {})
    status = video.get("status", {})

    title = snippet.get("title", "제목 없음")
    description = snippet.get("description", "").strip()
    tags = snippet.get("tags", [])
    category_id = snippet.get("categoryId", "")
    published_at = snippet.get("publishedAt", "")[:10]
    privacy = status.get("privacyStatus", "unknown")

    views = fmt_num(stats.get("viewCount", 0))
    likes = fmt_num(stats.get("likeCount", 0))
    comments = fmt_num(stats.get("commentCount", 0))
    duration = format_duration(content_details.get("duration", "PT0S"))

    video_id = video.get("id", "")
    url = f"https://www.youtube.com/watch?v={video_id}"

    # 첫 줄(요약)
    first_line = description.split("\n")[0] if description else "설명 없음"
    summary = f"{title} — {first_line}" if first_line else title

    # 태그 → [[태그]] 형식
    tag_links = " ".join(f"[[{t}]]" for t in tags) if tags else "태그 없음"

    # Related Topics: 태그 목록
    related = ", ".join(f"[[{t}]]" for t in tags[:10]) if tags else "없음"

    # 설명 정리 (너무 길면 앞 3000자만)
    full_desc = description[:3000] + ("..." if len(description) > 3000 else "")

    md = f"""# [[{title}]]

## 📌 Brief Summary
{summary}

## 📖 Core Content

### 영상 정보
| 항목 | 내용 |
|------|------|
| 🎬 영상 URL | [{url}]({url}) |
| 📅 업로드 날짜 | {published_at} |
| ⏱ 재생 시간 | {duration} |
| 🔒 공개 여부 | {privacy} |
| 👁 조회수 | {views} |
| 👍 좋아요 | {likes} |
| 💬 댓글 | {comments} |

### 설명
{full_desc if full_desc else "_(설명 없음)_"}

### 태그
{tag_links}

## 🔗 Knowledge Connections
- **Related Topics:** {related}
- **Projects/Contexts:** [[{channel_title}]]
- **Contradictions/Notes:** 카테고리 ID: {category_id}

---
*Last updated: {TODAY}*
"""
    return md


# ──────────────────────────────────────────────
# 마크다운 생성: 채널 인덱스
# ──────────────────────────────────────────────
def build_index_md(channel_info: dict, videos: list) -> str:
    channel_title = channel_info["title"]
    rows = []
    for v in videos:
        snippet = v.get("snippet", {})
        stats = v.get("statistics", {})
        title = snippet.get("title", "제목 없음")
        published_at = snippet.get("publishedAt", "")[:10]
        views = fmt_num(stats.get("viewCount", 0))
        fname = safe_filename(title)
        rows.append(f"| [[{fname}\\|{title}]] | {published_at} | {views} |")

    table = "\n".join(rows) if rows else "_(영상 없음)_"

    md = f"""# [[{channel_title}]] — 채널 인덱스

## 📌 Brief Summary
{channel_info['description'][:300] if channel_info['description'] else '채널 설명 없음'}

## 📖 채널 통계
| 항목 | 수치 |
|------|------|
| 👥 구독자 | {fmt_num(channel_info['subscriber_count'])} |
| 🎬 총 영상 수 | {fmt_num(channel_info['video_count'])} |
| 👁 총 조회수 | {fmt_num(channel_info['view_count'])} |

## 🗂 전체 영상 목록
| 제목 | 업로드일 | 조회수 |
|------|----------|--------|
{table}

## 🔗 Knowledge Connections
- **Related Topics:** 없음
- **Projects/Contexts:** YouTube 채널
- **Contradictions/Notes:** 자동 생성된 인덱스 파일입니다.

---
*Last updated: {TODAY}*
"""
    return md


# ──────────────────────────────────────────────
# 메인
# ──────────────────────────────────────────────
def main():
    print("=" * 60)
    print("  YouTube 채널 → 지식 파일 변환기")
    print("=" * 60)

    # 1. 인증
    youtube = get_authenticated_service()

    # 2. 채널 정보
    print("\n📡 채널 정보 조회 중...")
    channel_info = get_channel_info(youtube)
    print(f"   채널명: {channel_info['title']}")
    print(f"   구독자: {fmt_num(channel_info['subscriber_count'])}")
    print(f"   총 영상: {channel_info['video_count']}개")

    # 3. 영상 ID 수집
    print("\n📋 영상 목록 수집 중...")
    video_ids = get_all_video_ids(youtube, channel_info["uploads_playlist_id"])

    if not video_ids:
        print("⚠️  영상이 없습니다.")
        return

    # 4. 상세 정보 수집
    print("\n🔍 영상 상세 정보 수집 중...")
    videos = get_video_details(youtube, video_ids)
    print(f"   {len(videos)}개 영상 상세 정보 수집 완료")

    # 5. 출력 디렉토리 생성
    VIDEOS_DIR.mkdir(parents=True, exist_ok=True)

    # 6. 영상별 마크다운 생성
    print("\n✍️  마크다운 파일 생성 중...")
    failed = []
    for i, video in enumerate(videos):
        title = video.get("snippet", {}).get("title", "untitled")
        fname = safe_filename(title)
        filepath = VIDEOS_DIR / f"{fname}.md"

        try:
            md_content = build_video_md(video, channel_info["title"])
            filepath.write_text(md_content, encoding="utf-8")
            print(f"   [{i+1:3d}/{len(videos)}] ✅ {fname}.md")
        except Exception as e:
            print(f"   [{i+1:3d}/{len(videos)}] ❌ 실패: {title} ({e})")
            failed.append(title)

    # 7. 인덱스 생성
    print("\n📑 채널 인덱스 파일 생성 중...")
    index_md = build_index_md(channel_info, videos)
    (OUTPUT_DIR / "index.md").write_text(index_md, encoding="utf-8")
    print(f"   ✅ knowledge/index.md 생성 완료")

    # 8. 요약 출력
    print("\n" + "=" * 60)
    print(f"✅ 완료!")
    print(f"   생성된 파일: {len(videos) - len(failed)}개")
    if failed:
        print(f"   실패: {len(failed)}개")
        for t in failed:
            print(f"     - {t}")
    print(f"   출력 경로: {OUTPUT_DIR.resolve()}")
    print("=" * 60)


if __name__ == "__main__":
    main()
