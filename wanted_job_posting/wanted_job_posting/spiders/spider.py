import scrapy
import pymongo
from datetime import datetime
from wanted_job_posting.models import WantedJobPosting


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
                url="https://www.wanted.co.kr/api/v4/jobs?limit=20&offset=0&country=kr&job_sort=job.latest_order&years=-1&locations=all",
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
            detail_url = f"https://www.wanted.co.kr/api/v4/jobs/{job_id}"
            html_url = f"https://www.wanted.co.kr/wd/{job_id}"

            if html_url in self.crawled_urls:
                self.logger.debug(f"이미 수집된 URL: {html_url}")
                continue

            self.collected_count += 1
            yield scrapy.Request(detail_url, callback=self.parse_detail, meta={"html_url": html_url})

        # 다음 페이지 요청
        if len(jobs) == 20 and len(self.crawled_urls) < self.max_jobs:
            next_offset = offset + 20
            next_url = response.url.replace(f"offset={offset}", f"offset={next_offset}")
            yield scrapy.Request(next_url, callback=self.parse_list)

    def parse_detail(self, response):
        try:
            job_data = response.json()
            job = job_data.get("job", {})
            detail_data = job.get("detail", {})
            html_url = response.meta.get("html_url", response.url.replace("/api/v4/jobs/", "/wd/"))
            address = job.get("address", {})
            company = job.get("company", {})

            item = WantedJobPosting(
                metadata={
                    "source": "Wanted",
                    "sourceUrl": html_url,
                    "crawledAt": datetime.now().isoformat()
                },
                sourceData=job_data,
                externalUrl=html_url,
                status="active" if job.get("status") == "active" else "closed",
                due_time=job.get("due_time"),
                detail={
                    "position": {
                        "jobGroup": "기타",
                        "job": job.get("position", "기타")
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
                title_images=[img.get("url") for img in job.get("company_images", [])]
            )

            self._log_crawl(html_url)
            yield item.to_dict()

        except Exception as e:
            self.logger.error(f"채용공고 파싱 실패: {response.url}, 에러: {e}")

    def _log_crawl(self, url: str):
        """
        크롤링한 채용공고 URL을 MongoDB에 기록 (upsert 방식)
        """
        try:
            log = {
                "url": url,
                "purposes": ["job_posting"],
                "crawledAt": datetime.now().isoformat()
            }
            client = pymongo.MongoClient(self.settings.get("MONGO_URI"))
            db = client[self.settings.get("MONGO_DATABASE")]
            collection = db[self.settings.get("MONGO_LOG_COLLECTION")]
            collection.update_one({"url": url}, {"$set": log}, upsert=True)
            client.close()
            self.logger.info(f"크롤링 기록 저장 완료: {url}")
        except Exception as e:
            self.logger.error(f"크롤링 기록 저장 실패: {url}, 에러: {e}")
