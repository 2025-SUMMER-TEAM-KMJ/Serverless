# 📝 원티드 기업 정보 크롤러 (Wanted Company Profile Scraper)

이 프로젝트는 Scrapy 프레임워크를 사용하여 [원티드(Wanted)](https://www.wanted.co.kr/) 사이트의 기업 상세 페이지에서 기업 정보를 수집하는 크롤러입니다.  
수집된 데이터는 MongoDB에 저장되며, 실행 모드 및 범위 설정을 통해 효율적인 데이터 수집 및 관리가 가능합니다.

---

## 🚀 주요 기능

- **크롤링 모드**
  - `create`: 수집되지 않은 기업만 신규 수집합니다. (기본값)
  - `update`: 이전에 수집된 기업들의 데이터를 최신 상태로 갱신합니다.
- **company_id 순회 수집**: `1 ~ max_company_id` 범위 내에서 자동 순회 수집
- **중복 수집 방지**: MongoDB에 저장된 로그 기반으로 중복 방지
- **부분 수집 제어**: `max_companies` 인자를 통해 최대 수집 기업 수 제한
- **에러 처리 및 로깅**: 요청 실패 및 데이터 누락에 대한 에러 로깅 지원
- **환경 변수 관리**: `.env` 파일을 통해 민감한 DB 설정 분리 가능
- **CI/CD 지원**: GitHub Actions 등 자동화된 실행 환경에 적합

---

## 🛠️ 기술 스택

| 역할             | 도구                                                                 |
|------------------|----------------------------------------------------------------------|
| 크롤링           | [Scrapy](https://scrapy.org/)                                        |
| 데이터베이스     | [MongoDB](https://www.mongodb.com/)                                  |
| MongoDB 드라이버 | [Pymongo](https://pymongo.readthedocs.io/)                           |
| 환경 변수 관리   | [python-dotenv](https://pypi.org/project/python-dotenv/)             |

---

## 📁 프로젝트 구조

```text
wanted_company_profile/
├── .env.example
├── .gitignore
├── README.md
├── scrapy.cfg
└── wanted_company_profile/
    ├── __init__.py
    ├── pipelines.py           # MongoDB 저장 파이프라인
    ├── settings.py
    └── spiders/
        └── wanted_company_profiles.py  # 핵심 스파이더 로직
```

---

## ⚙️ 실행 예시

```bash
# 기본 실행 (신규 기업 수집, 최대 500개 기업), max_company_id는 생략 가능하며, 얼마나 수집 가능한지 확인 필요
scrapy crawl wanted_company_profiles -a mode=create -a max_company_id=10000 -a max_companies=500

# 업데이트 모드 실행
scrapy crawl wanted_company_profiles -a mode=update