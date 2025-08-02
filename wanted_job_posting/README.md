# 📝 원티드 채용공고 크롤러 (Wanted Job Posting Scraper)

이 프로젝트는 Scrapy 프레임워크를 사용하여 [원티드(Wanted)](https://www.wanted.co.kr/) 사이트에서 채용 공고를 수집하는 크롤러입니다. 수집된 데이터는 MongoDB에 저장되며, 유연한 크롤링 옵션을 통해 효율적인 데이터 수집 및 관리가 가능합니다.

---

## 🚀 주요 기능

- **크롤링 모드**
  - `create`: 신규 채용 공고만 수집합니다. (기본값)
  - `update`: 기존 데이터를 최신 상태로 갱신합니다.
- **중복 수집 방지**: MongoDB에 저장된 로그를 통해 이미 수집된 공고는 건너뜁니다.
- **수집 범위 제어**: 최대 수집 공고 수를 인자로 지정 가능 (`max_jobs`).
- **데이터 유효성 검증**: `jsonschema`로 데이터 구조 검증.
- **환경 변수 분리**: `.env`를 통해 민감 정보 분리.
- **CI/CD 연동 지원**: GitHub Actions에서 자동 실행 가능.

---

## 🛠️ 기술 스택

| 역할             | 도구                                                                 |
|------------------|----------------------------------------------------------------------|
| 크롤링           | [Scrapy](https://scrapy.org/)                                        |
| 데이터베이스     | [MongoDB](https://www.mongodb.com/)                                  |
| MongoDB 드라이버 | [Pymongo](https://pymongo.readthedocs.io/)                           |
| 환경 변수 관리   | [python-dotenv](https://pypi.org/project/python-dotenv/)             |
| 데이터 검증      | [jsonschema](https://python-jsonschema.readthedocs.io/)              |

---

## 📁 프로젝트 구조

```text
wanted_scraper/
├── .env.example
├── .gitignore
├── README.md
├── scrapy.cfg
└── wanted_scraper/
    ├── __init__.py
    ├── items.py               # WantedJobPosting 클래스 정의
    ├── middlewares.py
    ├── pipelines.py           # MongoDB 저장 파이프라인
    ├── settings.py
    └── spiders/
        └── wanted_jobs.py     # 핵심 스파이더 로직
```

---

## ▶️ 실행 예시

```bash
# 기본 실행 (신규 채용공고 수집, 최대 100개 공고 수집)
scrapy crawl wanted_job_postings -a mode=create -a max_jobs=100
```
```bash
# 업데이트 모드 실행 (기존 채용공고 정보 최신화)
scrapy crawl wanted_job_postings -a mode=update
```
