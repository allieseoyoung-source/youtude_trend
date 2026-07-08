"""
유튜브 트렌드 자동 수집기
-------------------------
1) 지정한 키워드로 최근 업로드된 영상을 검색
2) 한국(KR) 인기 급상승 영상도 함께 조회
3) 업로드 후 경과 시간 대비 조회수(=떡상 속도)를 계산
4) 결과를 구글 시트에 자동으로 append

필요한 환경변수 (GitHub Actions Secrets 또는 로컬 .env):
- YOUTUBE_API_KEY            : YouTube Data API v3 키
- GOOGLE_SHEET_ID            : 결과를 적을 구글 시트 ID (URL의 /d/ 뒤 문자열)
- GOOGLE_SERVICE_ACCOUNT_JSON: 서비스 계정 JSON 파일 "전체 내용" (문자열)
"""

import os
import json
import datetime as dt
from googleapiclient.discovery import build
import gspread
from google.oauth2.service_account import Credentials

# ---------------------------------------------------------------------------
# 1. 설정 - 여기 키워드만 바꿔가며 계속 튜닝하면 돼
# ---------------------------------------------------------------------------
KEYWORDS = [
    "마시멜로 챌린지",
    "디저트 신제품",
    "코스트코 신상",
    "미국 코스트코",
    "스낵 챌린지",
    "먹방 챌린지",
    "viral snack",
    "marshmallow recipe",
]

MAX_RESULTS_PER_KEYWORD = 10          # 키워드당 가져올 영상 수
PUBLISHED_WITHIN_DAYS = 3             # 최근 며칠 이내 업로드만 검색
MIN_VIEW_VELOCITY = 500               # 시간당 조회수 이 값 이상만 "주목할 영상"으로 채택
REGION_FOR_TRENDING = "KR"            # 급상승 차트 국가

SHEET_HEADER = [
    "수집일시", "구분(키워드/급상승)", "제목", "채널명",
    "게시일", "조회수", "경과시간(h)", "시간당조회수", "URL",
]


def get_youtube_client():
    api_key = os.environ["YOUTUBE_API_KEY"]
    return build("youtube", "v3", developerKey=api_key)


def hours_since(published_at: str) -> float:
    published = dt.datetime.strptime(published_at, "%Y-%m-%dT%H:%M:%SZ").replace(
        tzinfo=dt.timezone.utc
    )
    now = dt.datetime.now(dt.timezone.utc)
    return max((now - published).total_seconds() / 3600, 0.1)


def fetch_video_stats(youtube, video_ids):
    """video id 리스트로 통계(조회수 등) 한 번에 조회"""
    stats = {}
    for i in range(0, len(video_ids), 50):
        chunk = video_ids[i : i + 50]
        resp = youtube.videos().list(part="statistics,snippet", id=",".join(chunk)).execute()
        for item in resp.get("items", []):
            stats[item["id"]] = item
    return stats


def search_by_keyword(youtube, keyword):
    published_after = (
        dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=PUBLISHED_WITHIN_DAYS)
    ).strftime("%Y-%m-%dT%H:%M:%SZ")

    resp = youtube.search().list(
        q=keyword,
        part="id",
        type="video",
        order="viewCount",
        publishedAfter=published_after,
        maxResults=MAX_RESULTS_PER_KEYWORD,
        relevanceLanguage="ko",
    ).execute()

    video_ids = [item["id"]["videoId"] for item in resp.get("items", [])]
    if not video_ids:
        return []

    stats = fetch_video_stats(youtube, video_ids)
    rows = []
    for vid, item in stats.items():
        view_count = int(item["statistics"].get("viewCount", 0))
        published_at = item["snippet"]["publishedAt"]
        elapsed = hours_since(published_at)
        velocity = round(view_count / elapsed, 1)

        if velocity < MIN_VIEW_VELOCITY:
            continue

        rows.append([
            dt.datetime.now().strftime("%Y-%m-%d %H:%M"),
            f"키워드:{keyword}",
            item["snippet"]["title"],
            item["snippet"]["channelTitle"],
            published_at,
            view_count,
            round(elapsed, 1),
            velocity,
            f"https://www.youtube.com/watch?v={vid}",
        ])
    return rows


def fetch_trending(youtube):
    resp = youtube.videos().list(
        part="snippet,statistics",
        chart="mostPopular",
        regionCode=REGION_FOR_TRENDING,
        maxResults=20,
    ).execute()

    rows = []
    for item in resp.get("items", []):
        view_count = int(item["statistics"].get("viewCount", 0))
        published_at = item["snippet"]["publishedAt"]
        elapsed = hours_since(published_at)
        velocity = round(view_count / elapsed, 1)

        rows.append([
            dt.datetime.now().strftime("%Y-%m-%d %H:%M"),
            f"급상승({REGION_FOR_TRENDING})",
            item["snippet"]["title"],
            item["snippet"]["channelTitle"],
            published_at,
            view_count,
            round(elapsed, 1),
            velocity,
            f"https://www.youtube.com/watch?v={item['id']}",
        ])
    return rows


def get_sheet():
    creds_json = json.loads(os.environ["GOOGLE_SERVICE_ACCOUNT_JSON"])
    scopes = ["https://www.googleapis.com/auth/spreadsheets"]
    creds = Credentials.from_service_account_info(creds_json, scopes=scopes)
    gc = gspread.authorize(creds)
    sh = gc.open_by_key(os.environ["GOOGLE_SHEET_ID"])
    try:
        worksheet = sh.worksheet("트렌드수집")
    except gspread.WorksheetNotFound:
        worksheet = sh.add_worksheet(title="트렌드수집", rows=1000, cols=len(SHEET_HEADER))
        worksheet.append_row(SHEET_HEADER)
    return worksheet


def main():
    youtube = get_youtube_client()

    all_rows = []
    for kw in KEYWORDS:
        try:
            all_rows.extend(search_by_keyword(youtube, kw))
        except Exception as e:
            print(f"[경고] '{kw}' 검색 중 오류: {e}")

    try:
        all_rows.extend(fetch_trending(youtube))
    except Exception as e:
        print(f"[경고] 급상승 차트 조회 중 오류: {e}")

    if not all_rows:
        print("이번 실행에서는 조건에 맞는 영상이 없었어요.")
        return

    worksheet = get_sheet()
    # 헤더가 없으면 추가
    if worksheet.row_values(1) != SHEET_HEADER:
        worksheet.insert_row(SHEET_HEADER, 1)

    worksheet.append_rows(all_rows, value_input_option="USER_ENTERED")
    print(f"{len(all_rows)}개 영상을 시트에 추가했어요.")


if __name__ == "__main__":
    main()
