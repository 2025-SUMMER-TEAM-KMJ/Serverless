import scrapy
import pymongo
import json
from datetime import datetime


class Spider(scrapy.Spider):
    """
    원티드(wanted.co.kr)에서 기업 정보를 수집하는 Scrapy 기반 스파이더입니다.

    실행 모드:
    - create (기본값): MongoDB에 저장된 기존 기업 목록과 비교하여, 새로 추가된 기업만 수집합니다.
    - update: 이미 수집된 기업들을 다시 방문하여, 변경된 정보가 있을 경우 최신화합니다.

    실행 인자:
    - mode: 'create' 또는 'update' (예: -a mode=create)
    - max_companies: create 모드에서 수집할 최대 기업 수 (예: -a max_companies=100)
    - max_company_id: company_id의 최대값 (예: -a max_company_id=10000), max가 얼마인지는 조사 필요, 처음 시작은 1부터 수집해야 함
    """

    name = "wanted_company_profiles"

    def __init__(self, *args, **kwargs):
        super(Spider, self).__init__(*args, **kwargs)
        self.mode = kwargs.get("mode", "create").lower()
        if self.mode not in ["create", "update"]:
            raise ValueError("Mode must be 'create' or 'update'")

        self.collected_count = 0

        self.max_companies = int(kwargs.get("max_companies", 1000))
        self.max_company_id = int(kwargs.get("max_company_id", 100000))
        self.crawled_company_ids = set()

        if self.mode == "create":
            self._load_crawled_company_ids()

    @classmethod
    def from_crawler(cls, crawler, *args, **kwargs):
        spider = cls(settings=crawler.settings, *args, **kwargs)
        spider._set_crawler(crawler)
        return spider

    def _load_crawled_company_ids(self):
        """
        MongoDB에서 이전에 수집한 기업 ID를 불러와 중복 수집을 방지합니다.
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
            cursor = collection.find({"purposes": "company_profile"}, {"company_id": 1})
            self.crawled_company_ids = {doc["company_id"] for doc in cursor}
            client.close()
            self.logger.info(f"기존에 수집된 기업 ID {len(self.crawled_company_ids)}개를 로딩했습니다.")
        except Exception as e:
            self.logger.error(f"MongoDB에서 중복 기업 ID 로딩 실패: {e}")

    def start_requests(self):
        if self.mode == "create":
            start_id = max(self.crawled_company_ids) + 1 if self.crawled_company_ids else 1
            for company_id in range(start_id, self.max_company_id + 1):
                if self.collected_count >= self.max_companies:
                    break
                if company_id in self.crawled_company_ids:
                    continue

                self.collected_count += 1
                url = f"https://www.wanted.co.kr/company/{company_id}"
                yield scrapy.Request(
                    url=url,
                    callback=self.parse_detail,
                    meta={"company_id": company_id},
                    headers={"User-Agent": "Mozilla/5.0"},
                    errback=self.handle_error,
                    dont_filter=True
                )

        elif self.mode == "update":
            yield from self._request_update_companies()

    def _request_update_companies(self):
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
            cursor = collection.find({"purposes": "company_profile"}, {"company_id": 1})

            for doc in cursor:
                company_id = doc["company_id"]
                url = f"https://www.wanted.co.kr/company/{company_id}"
                yield scrapy.Request(
                    url=url,
                    callback=self.parse_detail,
                    meta={"company_id": company_id},
                    headers={"User-Agent": "Mozilla/5.0"},
                    errback=self.handle_error,
                    dont_filter=True
                )

            client.close()
        except Exception as e:
            self.logger.error(f"MongoDB에서 업데이트 대상 기업 불러오기 실패: {e}")

    def parse_detail(self, response):
        try:
            company_id = response.meta["company_id"]
            script = response.css("script#__NEXT_DATA__::text").get()
            if not script:
                self.logger.warning(f"[SKIP] __NEXT_DATA__ 태그 없음: company_id={company_id}")
                return

            raw_data = json.loads(script)
            page_props = raw_data.get("props", {}).get("pageProps", {})
            queries = page_props.get("dehydrateState", {}).get("queries", [])
            if not queries:
                self.logger.warning(f"[SKIP] 기업 정보 없음: company_id={company_id}")
                return

            company_info = queries[0].get("state", {}).get("data", {})

            full_address = (
                    company_info.get("address", {}).get("geo_location", {})
                    .get("n_location", {})
                    .get("road_address")
                    or company_info.get("address", {}).get("full_location", "")
            )

            result = {
                "companyName": company_info.get("name"),
                "source": {
                    "url": f"https://www.wanted.co.kr/company/{company_id}",
                    "platform": "Wanted",
                    "crawledAt": datetime.now().isoformat()
                },
                "profile": {
                    "features": [tag.get("title") for tag in company_info.get("companyTags", []) if "title" in tag],
                    "avgSalary": company_info.get("salary", {}).get("salary"),
                    "address": {
                        "country": company_info.get("address", {}).get("country", "한국"),
                        "location": company_info.get("address", {}).get("location", ""),
                        "district": company_info.get("address", {}).get("district", ""),
                        "full_location": full_address
                    }
                },
                "metadata": {
                    "source": "Wanted",
                    "sourceUrl": f"https://www.wanted.co.kr/company/{company_id}",
                    "crawledAt": datetime.now().isoformat()
                },
                "sourceData": raw_data
            }

            self._log_crawl(company_id)
            yield result

        except Exception as e:
            self.logger.error(f"기업 프로필 파싱 실패: {response.url}, 에러: {e}")

    def handle_error(self, failure):
        company_id = failure.request.meta.get("company_id")
        self.logger.warning(f"[FAIL] 요청 실패: company_id={company_id}, reason={repr(failure.value)}")

    def _log_crawl(self, company_id: int):
        """
        수집 완료한 기업 ID를 MongoDB 로그에 저장합니다.
        """
        try:
            log = {
                "company_id": company_id,
                "purposes": ["company_profile"],
                "crawledAt": datetime.now().isoformat()
            }
            client = pymongo.MongoClient(self.settings.get("MONGO_URI"))
            db = client[self.settings.get("MONGO_DATABASE")]
            collection = db[self.settings.get("MONGO_LOG_COLLECTION")]
            collection.update_one({"company_id": company_id}, {"$set": log}, upsert=True)
            client.close()
            self.logger.info(f"기업 크롤링 기록 저장 완료: {company_id}")
        except Exception as e:
            self.logger.error(f"기업 크롤링 기록 저장 실패: {company_id}, 에러: {e}")
