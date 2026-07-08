# 유튜브 트렌드 자동 수집기 - 설정 가이드

한 번만 세팅해두면 매일 자동으로 구글 시트에 트렌드 영상이 쌓여.
순서대로 따라오면 돼 (전부 무료로 가능).

---

## 1. 구글 시트 준비
1. 새 구글 시트를 하나 만들어 (예: "트렌드 수집함").
2. 주소창 URL에서 `/d/` 다음, `/edit` 전까지의 문자열을 복사해둬.
   예: `https://docs.google.com/spreadsheets/d/1AbCdEfGhIjK.../edit`
   → `1AbCdEfGhIjK...` 이 부분이 `GOOGLE_SHEET_ID`

## 2. 구글 클라우드에서 API 키 + 서비스 계정 발급
1. https://console.cloud.google.com 접속 → 새 프로젝트 생성 (예: trend-collector)
2. 좌측 메뉴 "API 및 서비스 > 라이브러리"에서 아래 2개 검색 후 각각 "사용 설정":
   - **YouTube Data API v3**
   - **Google Sheets API**
3. "사용자 인증 정보 > 사용자 인증 정보 만들기 > API 키" → 생성된 키가 `YOUTUBE_API_KEY`
4. "사용자 인증 정보 만들기 > 서비스 계정" → 이름 아무거나 입력 후 생성
   - 생성된 서비스 계정 클릭 → "키" 탭 → "키 추가 > 새 키 만들기 > JSON" → 파일 다운로드됨
   - 이 JSON 파일을 텍스트 편집기로 열어서 **전체 내용을 복사** → 이게 `GOOGLE_SERVICE_ACCOUNT_JSON`
5. 다운받은 JSON 안에 있는 `client_email` 값(예: `xxx@xxx.iam.gserviceaccount.com`)을 복사해서,
   1번에서 만든 구글 시트의 "공유" 버튼 눌러 **편집자 권한으로 추가**해줘.
   (이 단계를 빼먹으면 스크립트가 시트에 쓰기 실패함)

## 3. GitHub에 올리기
1. GitHub 계정이 없으면 https://github.com 에서 가입 (무료).
2. 새 저장소(Repository) 생성 (Private로 해도 됨).
3. 이 폴더 전체(`collect_trends.py`, `requirements.txt`, `.github/workflows/trend-collect.yml`)를 그 저장소에 업로드.
   - GitHub 웹사이트에서 "Add file > Upload files"로 드래그해서 올려도 됨.

## 4. 비밀 키 등록 (Secrets)
저장소 페이지에서 **Settings > Secrets and variables > Actions > New repository secret** 으로 아래 3개를 등록:

| Name | Value |
|---|---|
| `YOUTUBE_API_KEY` | 2단계에서 발급받은 API 키 |
| `GOOGLE_SHEET_ID` | 1단계에서 복사한 시트 ID |
| `GOOGLE_SERVICE_ACCOUNT_JSON` | 2단계에서 복사한 JSON 파일 전체 내용 |

## 5. 확인
- 저장소의 **Actions** 탭 → "유튜브 트렌드 자동 수집" 워크플로우 선택 → **Run workflow** 버튼으로 한 번 수동 실행해봐.
- 성공하면 구글 시트에 "트렌드수집" 탭이 자동 생성되고 영상 목록이 채워져.
- 이후로는 매일 한국시간 오전 7시에 자동으로 실행돼 (원하면 `.github/workflows/trend-collect.yml`의 cron 시간 수정 가능).

---

## 커스터마이징
- `collect_trends.py` 상단의 `KEYWORDS` 리스트에 원하는 검색어를 자유롭게 추가/삭제하면 돼.
- `MIN_VIEW_VELOCITY` (시간당 조회수 기준)를 낮추면 더 많은 영상이, 높이면 더 엄선된 영상만 잡혀.
- `PUBLISHED_WITHIN_DAYS`로 "며칠 이내 업로드"만 볼지 조절 가능.

---

## 다음 단계 (인스타/틱톡 하이브리드 자동화)
인스타그램·틱톡은 공식 API로 "트렌드 발굴"을 자동화할 방법이 없어 (계정 무관 콘텐츠 접근이 막혀있음).
대신 이런 구조로 "저장 후 정리"를 자동화할 수 있어:

1. 릴스/영상 링크를 공유(Share) → 아이폰 단축어 또는 Make.com 웹훅으로 전송
2. 서버가 해당 URL의 공개 oEmbed 정보(제목, 썸네일, 작성자)를 자동으로 가져와서
3. 같은 구글 시트에 자동으로 한 줄 추가

이 부분도 원하면 이어서 만들어줄게 — 필요하면 말해줘.
