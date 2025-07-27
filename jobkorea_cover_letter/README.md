# 잡코리아 합격자소서 크롤러 (Jobkorea Cover Letter Scraper)

이 프로젝트는 Scrapy 프레임워크를 사용하여 [잡코리아](https://www.jobkorea.co.kr/) 사이트에서 합격 자기소개서를 수집하는 크롤러입니다. 수집된 데이터는 MongoDB에 저장되며, 유연한 크롤링 옵션을 제공하여 효율적인 데이터 수집 및 관리가 가능합니다.

## 주요 기능

-   **동적 크롤링 모드**:
    -   `create` 모드: 새로운 기업의 자기소개서만 선택적으로 수집합니다. (기본값)
    -   `update` 모드: 이미 수집된 모든 자기소개서를 다시 방문하여 데이터를 최신 상태로 갱신합니다.
-   **중복 수집 방지**: MongoDB에 저장된 로그를 확인하여 이미 방문한 기업의 자소서 목록 페이지는 건너뛰어 불필요한 요청을 줄입니다.
-   **수집 범위 제어**: 명령어 인자를 통해 크롤링할 최대 기업 수와 기업당 최대 자소서 수를 동적으로 조절할 수 있습니다.
-   **데이터 유효성 검증**: `jsonschema`를 사용하여 수집된 데이터가 사전에 정의된 스키마를 준수하는지 검증합니다.
-   **민감 정보 관리**: `.env` 파일을 통해 MongoDB 연결 정보 등 민감한 설정을 코드와 분리하여 안전하게 관리합니다.
-   **CI/CD 환경 지원**: GitHub Actions 환경을 자동으로 감지하여 Secrets를 통해 주입된 환경 변수를 사용하도록 설계되었습니다.

## 기술 스택

-   **크롤링**: [Scrapy](https://scrapy.org/)
-   **데이터베이스**: [MongoDB](https://www.mongodb.com/) (데이터 및 로그 저장)
-   **데이터베이스 드라이버**: [Pymongo](https://pymongo.readthedocs.io/en/stable/)
-   **환경 변수 관리**: [python-dotenv](https://pypi.org/project/python-dotenv/)
-   **데이터 검증**: [jsonschema](https://python-jsonschema.readthedocs.io/en/stable/)

## 프로젝트 구조

```
jobkorea_scraper/
├── .env.example         # .env 파일 예시
├── .gitignore
├── README.md
├── scrapy.cfg
└── jobkorea_scraper/
    ├── __init__.py
    ├── items.py         # 데이터 구조(JobkoreaCoverLetter 클래스) 정의
    ├── middlewares.py
    ├── pipelines.py     # MongoDB 저장 파이프라인
    ├── settings.py      # 프로젝트 설정 (환경 변수 로드)
    └── spiders/
        └── jobkorea_cover_letters.py # 핵심 스파이더 로직
```

## 설치 및 설정

### 1. 사전 요구사항

-   Python 3.8 이상
-   MongoDB 서버 실행

### 2. 프로젝트 클론 및 라이브러리 설치

```bash
# 프로젝트 클론
git clone <your-repository-url>
cd jobkorea_scraper

# 가상환경 생성 및 활성화 (권장)
python -m venv venv
source venv/bin/activate  # macOS/Linux
# venv\Scripts\activate    # Windows

# 필요한 라이브러리 설치
pip install -r requirements.txt
```
*(참고: `requirements.txt` 파일이 없다면 아래 명령어로 직접 설치하세요.)*
```bash
pip install scrapy pymongo python-dotenv jsonschema
```

### 3. 환경 변수 설정

프로젝트 루트 디렉토리에 `.env` 파일을 생성하고, 아래 내용을 참고하여 MongoDB 연결 정보를 입력합니다.

```bash
# .env.example 파일을 .env로 복사하여 사용
cp .env.example .env
```

**.env 파일 내용:**
```dotenv
# MongoDB 연결 URI
MONGO_URI="mongodb://localhost:27017/"

# 사용할 데이터베이스 이름
MONGO_DATABASE="jobkorea_db"

# 자소서 데이터를 저장할 컬렉션 이름
MONGO_COLLECTION="cover_letters"

# 크롤링 로그를 저장할 컬렉션 이름
MONGO_LOG_COLLECTION="master_crawler_logs"
```

## 스파이더 실행 방법

모든 명령어는 프로젝트의 최상위 디렉토리(`scrapy.cfg` 파일이 있는 곳)에서 실행해야 합니다.

### `create` 모드 (새로운 데이터 수집)

가장 일반적으로 사용하는 모드입니다. DB에 기록된 로그를 바탕으로 아직 방문하지 않은 기업의 자소서를 수집합니다.

-   **기본 실행 (기업 5개, 기업당 자소서 10개 수집)**:
    ```bash
    scrapy crawl jobkorea_cover_letters
    ```
    또는 명시적으로:
    ```bash
    scrapy crawl jobkorea_cover_letters -a mode=create
    ```

-   **수집 범위 지정 실행**:
    ```bash
    # 기업 3개, 기업당 자소서 5개 수집
    scrapy crawl jobkorea_cover_letters -a max_companies=3 -a max_essays_per_company=5
    ```

### `update` 모드 (기존 데이터 갱신)

DB에 저장된 모든 자소서 URL을 다시 방문하여 데이터를 재파싱하고 덮어씁니다. 파싱 로직을 변경했거나 데이터를 최신화하고 싶을 때 사용합니다.

```bash
scrapy crawl jobkorea_cover_letters -a mode=update
```
*(참고: `update` 모드에서는 `max_companies`와 `max_essays_per_company` 인자가 무시됩니다.)*

### 테스트 (파싱 결과만 파일로 확인)

MongoDB에 저장하지 않고 파싱이 잘 되는지만 확인하고 싶을 경우, `-o` (output) 옵션을 사용하세요. 이 옵션은 파이프라인을 비활성화하고 결과를 파일로 저장합니다.

```bash
scrapy crawl jobkorea_cover_letters -o results.json
```
크롤링이 완료되면 `results.json` 파일에서 파싱된 데이터를 확인할 수 있습니다.

## GitHub Actions 연동

이 프로젝트는 GitHub Actions 환경을 자동으로 감지합니다. 워크플로우에서 아래 Secrets를 설정하면, `.env` 파일 없이도 CI/CD 환경에서 안전하게 크롤러를 실행할 수 있습니다.

-   `MONGO_URI`
-   `MONGO_DATABASE`
-   `MONGO_COLLECTION`
-   `MONGO_LOG_COLLECTION`

**워크플로우 예시 (`.github/workflows/scrape.yml`):**
```yaml
name: Scrape Jobkorea Cover Letters

on:
  schedule:
    - cron: '0 0 * * *' # 매일 자정에 실행
  workflow_dispatch:

jobs:
  scrape:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout repository
        uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.10'

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install scrapy pymongo python-dotenv jsonschema

      - name: Run Scraper
        env:
          MONGO_URI: ${{ secrets.MONGO_URI }}
          MONGO_DATABASE: ${{ secrets.MONGO_DATABASE }}
          MONGO_COLLECTION: ${{ secrets.MONGO_COLLECTION }}
          MONGO_LOG_COLLECTION: ${{ secrets.MONGO_LOG_COLLECTION }}
        run: scrapy crawl jobkorea_cover_letters
```