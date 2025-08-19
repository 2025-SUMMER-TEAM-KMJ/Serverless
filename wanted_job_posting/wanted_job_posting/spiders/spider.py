import json
import re
from typing import Optional
import scrapy
import pymongo
from datetime import datetime
from wanted_job_posting.models import MasterJobPosting, WantedJobPosting


class Spider(scrapy.Spider):
    """
    원티드(wanted.co.kr)에서 채용공고를 수집하는 Scrapy 기반 스파이더입니다.

    실행 모드:
    - create (기본값): MongoDB에 저장된 기존 공고 목록과 비교하여, 새로 추가된 채용공고만 수집합니다.
    - update: 이미 수집된 공고들을 다시 방문하여, 변경된 정보가 있을 경우 최신화합니다.

    실행 인자:
    - mode: 'create' 또는 'update' (예: -a mode=create)
    - max_jobs: create 모드에서 수집할 최대 채용공고 수 (예: -a max_jobs=100)
    """

    name = "wanted_job_postings"

    def __init__(self, *args, **kwargs):
        super(Spider, self).__init__(*args, **kwargs)
        self.mode = kwargs.get("mode", "create").lower()
        if self.mode not in ["create", "update"]:
            raise ValueError("Mode must be 'create' or 'update'")

        self.collected_count = 0
        self.max_jobs = 1000
        if "max_jobs" in kwargs:
            try:
                self.max_jobs = int(kwargs["max_jobs"])
            except ValueError:
                self.logger.warning(f"max_jobs 인자값이 정수로 변환되지 않아 기본값 {self.max_jobs} 사용")
        self.job_sort = kwargs.get("job_sort", "job.latest_order")
        self.crawled_urls = set()

        if self.mode == "create":
            self._load_crawled_urls()

    @classmethod
    def from_crawler(cls, crawler, *args, **kwargs):
        spider = cls(settings=crawler.settings, *args, **kwargs)
        spider._set_crawler(crawler)
        return spider

    def _load_crawled_urls(self):
        """
        MongoDB에서 이전에 수집한 공고 URL을 불러와 중복 수집을 방지합니다.
        """
        mongo_uri = self.settings.get("MONGO_URI")
        mongo_db = self.settings.get("MONGO_DATABASE")
        mongo_log_collection = self.settings.get("MONGO_LOG_COLLECTION")
        if not all([mongo_uri, mongo_db, mongo_log_collection]):
            self.logger.warning("MongoDB log 설정이 누락되어 중복 체크를 건너뜁니다.")
            return

        try:
            client = pymongo.MongoClient(mongo_uri)
            db = client[mongo_db]
            collection = db[mongo_log_collection]
            cursor = collection.find({"purposes": "job_posting"}, {"url": 1})
            self.crawled_urls = {doc["url"] for doc in cursor}
            client.close()
            self.logger.info(f"기존에 수집된 URL {len(self.crawled_urls)}개를 로딩했습니다.")
        except Exception as e:
            self.logger.error(f"MongoDB에서 중복 URL 로딩 실패: {e}")

    def start_requests(self):
        """
        실행 모드에 따라 최초 요청을 보냅니다.
        """
        if self.mode == "create":
            yield scrapy.Request(
                url=f"https://www.wanted.co.kr/api/v4/jobs?limit=20&offset=0&country=kr&job_sort={self.job_sort}&years=-1&locations=all",
                callback=self.parse_list,
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
                }
            )
        elif self.mode == "update":
            self._request_update_jobs()

    def _request_update_jobs(self):
        """
        update 모드일 경우 MongoDB에 저장된 모든 URL을 대상으로 상세 페이지 요청을 수행합니다.
        """
        mongo_uri = self.settings.get("MONGO_URI")
        mongo_db = self.settings.get("MONGO_DATABASE")
        mongo_log_collection = self.settings.get("MONGO_LOG_COLLECTION")

        if not all([mongo_uri, mongo_db, mongo_log_collection]):
            self.logger.error("MongoDB 설정이 누락되어 update 모드 실행 불가")
            return

        try:
            client = pymongo.MongoClient(mongo_uri)
            db = client[mongo_db]
            collection = db[mongo_log_collection]
            cursor = collection.find({"purposes": "job_posting"}, {"url": 1})

            for doc in cursor:
                yield scrapy.Request(url=doc["url"].replace("/wd/", "/api/v4/jobs/"), callback=self.parse_detail)

            client.close()
        except Exception as e:
            self.logger.error(f"MongoDB에서 업데이트 대상 URL을 불러오지 못했습니다: {e}")

    def parse_list(self, response):
        """
        채용공고 목록 페이지 응답을 파싱하여 상세 페이지 요청을 생성합니다.
        """
        data = response.json()
        jobs = data.get("data", [])
        offset = int(response.url.split("offset=")[-1].split("&")[0])

        for job in jobs:
            if self.max_jobs > 0 and self.collected_count >= self.max_jobs:
                return

            job_id = job.get("id")
            html_url = f"https://www.wanted.co.kr/wd/{job_id}"
            detail_url = f"https://www.wanted.co.kr/api/chaos/jobs/v4/{job_id}/details"

            if detail_url in self.crawled_urls:
                self.logger.debug(f"이미 수집된 URL: {detail_url}")
                continue

            self.collected_count += 1
            yield scrapy.Request(detail_url, callback=self.parse_detail, meta={"detail_url": detail_url, "html_url": html_url})

        # 다음 페이지 요청
        if self.collected_count < self.max_jobs:
            next_offset = offset + 20
            next_url = response.url.replace(f"offset={offset}", f"offset={next_offset}")
            yield scrapy.Request(next_url, callback=self.parse_list)

    def parse_detail(self, response):
        try:
            job_data = response.json()["data"]
            job = job_data.get("job", {})
            detail_data = job.get("detail", {})
            detail_url = response.meta.get("detail_url")
            html_url = response.meta.get("html_url")
            address = job.get("address", {})
            company = job.get("company", {})

            item = WantedJobPosting(
                metadata={
                    "source": "wanted",
                    "sourceUrl": detail_url,
                    "crawledAt": datetime.now().isoformat()
                },

                sourceData="",
                externalUrl=html_url,
                status="active" if job.get("status") == "active" else "closed",
                due_time=job.get("due_time"),
                detail={
                    "position": {
                        "jobGroup": job["category_tag"]["parent_tag"]["text"],
                        "job": ','.join([x["text"] for x in job["category_tag"]["child_tags"]])
                    },
                    "intro": detail_data.get("intro", ""),
                    "main_tasks": detail_data.get("main_tasks", ""),
                    "requirements": detail_data.get("requirements", ""),
                    "preferred_points": detail_data.get("preferred_points", ""),
                    "benefits": detail_data.get("benefits", ""),
                    "hire_rounds": detail_data.get("hire_rounds", "")
                },
                company={
                    "name": company.get("name", ""),
                    "logo_img": job.get("logo_img", {}).get("origin"),
                    "address": {
                        "country": address.get("country", ""),
                        "location": address.get("location", ""),
                        "district": address.get("district", ""),
                        "full_location": address.get("full_location", "")
                    }
                },
                skill_tags=[tag.get("title") for tag in job.get("skill_tags", [])],
                title_images=job.get("title_images", [])
            )

            item2 = MasterJobPosting(
                metadata={
                    "source": "wanted",
                    "sourceUrl": detail_url,
                    "crawledAt": datetime.now().isoformat()
                },

                sourceData="",
                externalUrl=html_url,
                status="active" if job.get("status") == "active" else "closed",
                due_time=job.get("due_time"),
                detail={
                    "position": {
                        "jobGroup": job["category_tag"]["parent_tag"]["text"],
                        "job": [x["text"] for x in job["category_tag"]["child_tags"]]
                    },
                    "intro": detail_data.get("intro", ""),
                    "main_tasks": detail_data.get("main_tasks", ""),
                    "requirements": detail_data.get("requirements", ""),
                    "preferred_points": detail_data.get("preferred_points", ""),
                    "benefits": detail_data.get("benefits", ""),
                    "hire_rounds": detail_data.get("hire_rounds", "")
                },
                company={
                    "name": company.get("name", ""),
                    "logo_img": job.get("logo_img", {}).get("origin"),
                    "address": {
                        "country": address.get("country", ""),
                        "location": address.get("location", ""),
                        "district": address.get("district", ""),
                        "full_location": address.get("full_location", "")
                    }
                },
                skill_tags=[tag.get("title") for tag in job.get("skill_tags", [])],
                title_images=job.get("title_images", [])
            )

            yield item

            company_id = job.get("company", {}).get("id")
            if company_id:
                company_page_url = f"https://www.wanted.co.kr/company/{company_id}/"
                self.logger.info(f"{company_page_url} 에서 기업 정보 파싱 시작")
                yield scrapy.Request(
                    url=company_page_url,
                    callback=self.parse_company,
                    headers={
                        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
                        'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7',
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36',
                        'Referer': 'https://www.wanted.co.kr/',  # 실제 방문 직전 페이지 URL로 변경
                        'Connection': 'keep-alive',
                        'Accept-Encoding': 'gzip, deflate, br',
                        'Upgrade-Insecure-Requests': '1',
                        'Cache-Control': 'max-age=0',
                        # 필요하다면 쿠키도 추가 가능
                        # 'Cookie': '쿠키값들',
                    },
                    meta={"job_data": item2}
                )
            
        except Exception as e:
            self.logger.error(f"채용공고 파싱 실패: {response.url}, 에러: {e}")

    def parse_company(self, response):
        """
        [최종 업그레이드] 오직 __NEXT_DATA__ JSON만을 파싱하여 모든 기업 정보를 추출합니다.
        """
        job_post_object = response.meta["job_data"]

        try:
            # 1. __NEXT_DATA__ 스크립트 태그에서 JSON 데이터 추출 및 파싱
            next_data_str = response.xpath('//script[@id="__NEXT_DATA__"]/text()').get()
            if not next_data_str:
                raise ValueError("__NEXT_DATA__ script tag not found.")
            
            data = json.loads(next_data_str)
            
            # 데이터가 담겨있는 queries 리스트 경로로 이동
            queries = data.get("props", {}).get("pageProps", {}).get("dehydrateState", {}).get("queries", [])

            # 2. 'companyInfo' 키에서 데이터 추출 (태그 등)
            company_info = next((q['state']['data'] for q in queries if q.get('queryKey', [None])[0] == 'companyInfo'), None)
            
            if company_info:
                # 'features'에 회사 태그 할당
                tags = [tag.get('title') for tag in company_info.get('companyTags', []) if tag.get('title')]
                job_post_object.company["features"] = tags
            else:
                job_post_object.company["features"] = []

            # 3. 'companySummary' 키에서 핵심 수치 데이터 추출 (연봉 등)
            company_summary = next((q['state']['data'] for q in queries if q.get('queryKey', [None])[0] == 'companySummary'), None)

            if company_summary:
                # __NEXT_DATA__의 salary.salary 값은 '원' 단위 정수입니다.
                # MasterJobPosting 스키마가 '만원' 단위 정수를 원한다면 10000으로 나눠줍니다.
                avg_salary_won = company_summary.get("salary", {}).get("salary")
                job_post_object.company["avgSalary"] = int(avg_salary_won) if avg_salary_won else None
                
                # 신규 입사자 연봉 데이터 키를 찾아서 할당
                # 해당 키가 없을 수 있으므로 .get()으로 안전하게 접근
                newbie_salary_won = company_summary.get("employee", {}).get("newbie_salary") # 실제 키 확인 필요
                job_post_object.company["avgEntrySalary"] = int(newbie_salary_won) if newbie_salary_won else None
            else:
                job_post_object.company["avgSalary"] = None
                job_post_object.company["avgEntrySalary"] = None

            self.logger.info(f"__NEXT_DATA__ 파싱 완료: {job_post_object.company['name']} "
                             f"(평균연봉: {job_post_object.company['avgSalary']}, "
                             f"신규입사자연봉: {job_post_object.company['avgEntrySalary']})")
            
            # 4. 모든 정보가 채워진 객체를 to_dict()로 변환하여 반환
            yield job_post_object

        except Exception as e:
            self.logger.error(f"기업정보 결합 또는 검증 실패(__NEXT_DATA__): {response.url}, 에러: {e}", exc_info=True)
            # ... (Fallback 로직은 동일) ...
            try:
                job_post_object.company["features"] = job_post_object.company.get("features", [])
                job_post_object.company["avgSalary"] = None
                job_post_object.company["avgEntrySalary"] = None
                yield job_post_object
            except Exception as final_e:
                self.logger.critical(f"Fallback 데이터 생성조차 실패: {getattr(job_post_object, 'externalUrl', 'N/A')}, 에러: {final_e}")