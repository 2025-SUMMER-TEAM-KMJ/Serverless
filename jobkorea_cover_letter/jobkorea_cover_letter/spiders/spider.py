# jobkorea_scraper/spiders/jobkorea_spider.py

import scrapy
import re
import pymongo
from datetime import datetime
from urllib.parse import urlparse
from jobkorea_cover_letter.models import JobkoreaCoverLetter

class Spider(scrapy.Spider):
    """
    잡코리아에서 합격자소서를 크롤링하는 스파이더.

    실행 모드:
    - create (기본값): 새로운 기업의 자소서를 수집합니다. 이미 방문한 기업은 건너뜁니다.
    - update: MongoDB에 저장된 기존의 모든 자소서 URL을 다시 방문하여 데이터를 갱신합니다.

    실행 인자:
    - mode: 'create' 또는 'update' (예: -a mode=create)
    - max_companies: create 모드에서 수집할 최대 기업 수 (예: -a max_companies=10)
    - max_essays_per_company: create 모드에서 기업당 수집할 최대 자소서 수 (예: -a max_essays_per_company=20)
    """
    name = 'jobkorea_cover_letter'

    def __init__(self, *args, **kwargs):
        """
        스파이더 초기화. 명령어 인자를 받고 모드에 따라 필요한 데이터를 준비합니다.
        """
        super(Spider, self).__init__(*args, **kwargs)
        
        # 1. 모드 및 인자 설정
        self.mode = kwargs.get('mode', 'create').lower()
        if self.mode not in ['create', 'update']:
            raise ValueError("Mode must be either 'create' or 'update'")

        self.max_companies = int(kwargs.get('max_companies', 5))
        self.max_essays_per_company = int(kwargs.get('max_essays_per_company', 10))
        self.crawled_companies = 0
        
        self.logger.info(
            f"Spider initialized in '{self.mode}' mode with settings: "
            f"max_companies={self.max_companies}, "
            f"max_essays_per_company={self.max_essays_per_company}"
        )

        # 2. 'create' 모드일 경우에만 중복 체크를 위해 기존 로그 불러오기
        self.crawled_passassay_urls = set()
        if self.mode == 'create':
            self._load_crawled_urls()

    def _load_crawled_urls(self):
        """
        (create 모드 전용) MongoDB에서 이미 크롤링된 PassAssay URL 목록을 불러옵니다.
        """
        mongo_uri = self.settings.get('MONGO_URI')
        mongo_db = self.settings.get('MONGO_DATABASE')
        log_collection_name = self.settings.get('MONGO_LOG_COLLECTION')

        if not all([mongo_uri, mongo_db, log_collection_name]):
            self.logger.warning("MongoDB log settings are not fully configured. Will not check for duplicates.")
            return

        try:
            client = pymongo.MongoClient(mongo_uri)
            db = client[mongo_db]
            log_collection = db[log_collection_name]
            
            cursor = log_collection.find(
                {'purposes': 'pass_assay_list'}, 
                {'url': 1, '_id': 0}
            )
            self.crawled_passassay_urls = {doc['url'] for doc in cursor}
            client.close()
            self.logger.info(f"Loaded {len(self.crawled_passassay_urls)} already crawled PassAssay URLs from MongoDB.")
        except pymongo.errors.ConnectionFailure as e:
            self.logger.error(f"Could not connect to MongoDB to fetch crawled URLs. Error: {e}")
        except Exception as e:
            self.logger.error(f"An unexpected error occurred while fetching crawled URLs. Error: {e}")

    @classmethod
    def from_crawler(cls, crawler, *args, **kwargs):
        spider = cls(settings=crawler.settings, *args, **kwargs)
        spider._set_crawler(crawler)
        return spider

    def start_requests(self):
        """
        모드에 따라 시작 요청을 다르게 생성합니다.
        """
        if self.mode == 'create':
            yield scrapy.Request('https://www.jobkorea.co.kr/Salary/Index?orderCode=2&coPage=1', self.parse)
        
        elif self.mode == 'update':
            mongo_uri = self.settings.get('MONGO_URI')
            mongo_db = self.settings.get('MONGO_DATABASE')
            log_collection_name = self.settings.get('MONGO_LOG_COLLECTION')

            if not all([mongo_uri, mongo_db, log_collection_name]):
                self.logger.error("MongoDB settings are required for 'update' mode.")
                return

            try:
                client = pymongo.MongoClient(mongo_uri)
                db = client[mongo_db]
                log_collection = db[log_collection_name]
                
                cursor = log_collection.find({'purposes': 'cover_letter'}, {'url': 1, '_id': 0})
                update_urls = [doc['url'] for doc in cursor]
                client.close()
                
                self.logger.info(f"Found {len(update_urls)} URLs to update.")
                for url in update_urls:
                    yield scrapy.Request(url, callback=self.parse_cover_letter)
            except Exception as e:
                self.logger.error(f"Failed to fetch URLs for update mode. Error: {e}")

    def parse(self, response):
        """
        1단계 (create 모드 전용): 연봉 정보 페이지에서 기업 목록을 파싱합니다.
        """
        if self.mode != 'create':
            return

        self.logger.info(f"Parsing company list from: {response.url}")
        
        company_links = response.css('ul#listCompany > li > a::attr(href)').getall()
        
        for link in company_links:
            if self.crawled_companies >= self.max_companies:
                self.logger.info(f"Reached max companies to crawl: {self.max_companies}.")
                return

            parsed_url = urlparse(link)
            path_parts = parsed_url.path.split('/')
            
            if len(path_parts) > 2 and path_parts[1] == 'Company':
                company_id = path_parts[2]
                pass_assay_url = f"https://www.jobkorea.co.kr/company/{company_id}/PassAssay"
                
                if pass_assay_url in self.crawled_passassay_urls:
                    self.logger.info(f"Skipping already crawled URL: {pass_assay_url}")
                    continue

                self.crawled_companies += 1
                yield response.follow(
                    pass_assay_url, 
                    callback=self.parse_company_essays,
                    meta={'crawled_essays': 0, 'pass_assay_url': pass_assay_url}
                )

        if self.crawled_companies < self.max_companies:
            next_page_link = response.css('div.paginations a.next::attr(data-page)').get()
            if next_page_link:
                yield response.follow(f"https://www.jobkorea.co.kr/Salary/Index?orderCode=2&coPage={next_page_link}", self.parse)

    def parse_company_essays(self, response):
        """
        2단계 (create 모드 전용): 기업별 합격자소서 목록 페이지를 파싱하고 로그를 기록합니다.
        """
        pass_assay_url = response.meta['pass_assay_url']
        crawled_essays_count = response.meta['crawled_essays']
        self.logger.info(f"Parsing essay list from: {response.url} (Crawled essays for this company: {crawled_essays_count})")

        essay_links = response.css('div.starList li.assay a::attr(href)').getall()

        if crawled_essays_count == 0 and essay_links:
            self.log_crawl_purpose(pass_assay_url, 'pass_assay_list')

        for link in essay_links:
            if crawled_essays_count >= self.max_essays_per_company:
                self.logger.info(f"Reached max essays ({self.max_essays_per_company}) for {pass_assay_url}.")
                return

            yield response.follow(link, callback=self.parse_cover_letter)
            crawled_essays_count += 1
        
        if crawled_essays_count < self.max_essays_per_company and essay_links:
            current_page_num_tag = response.css('div.tplPagination span.now')
            if current_page_num_tag:
                current_page_num = int(current_page_num_tag.css('::text').get())
                next_page_num = current_page_num + 1
                next_page_link = response.css(f'div.tplPagination a[data-page="{next_page_num}"]::attr(href)').get()
                
                if next_page_link:
                    yield response.follow(
                        next_page_link, 
                        callback=self.parse_company_essays,
                        meta={'crawled_essays': crawled_essays_count, 'pass_assay_url': pass_assay_url}
                    )

    def log_crawl_purpose(self, url, purpose):
        """
        주어진 URL에 대한 크롤링 목적과 시각을 MongoDB에 기록하는 헬퍼 메서드.
        """
        try:
            client = pymongo.MongoClient(self.settings.get('MONGO_URI'))
            db = client[self.settings.get('MONGO_DATABASE')]
            log_collection = db[self.settings.get('MONGO_LOG_COLLECTION')]
            
            log_collection.update_one(
                {'url': url},
                {
                    '$addToSet': {'purposes': purpose},
                    '$set': {'crawledAt': datetime.now().isoformat()}
                },
                upsert=True
            )
            client.close()
            self.logger.info(f"Logged purpose '{purpose}' for URL: {url}")
        except Exception as e:
            self.logger.error(f"Failed to log purpose '{purpose}' for URL {url} to MongoDB. Error: {e}")
    
    def parse_cover_letter(self, response):
        """
        3단계 (create/update 모드 공통): 개별 자소서 페이지를 파싱하고 Item을 생성합니다.
        """
        self.logger.info(f"Parsing cover letter: {response.url}")
        
        try:
            company_name = response.css('div.company-header-branding-body .name::text').get("").strip()
            title_text = response.css('article.detailView h2.tit::text').get("").strip()
            position_name = "unknown"
            application_at = None
            
            title_match = re.search(r'(\d{4}년 (?:상|하)반기)\s+(신입|경력)\s+(.+?)\s+합격자소서', title_text)
            if title_match:
                year_half, _, position = title_match.groups()
                position_name = position.strip()
                year_match = re.search(r'(\d{4})', year_half)
                if year_match:
                    year = year_match.group(1)
                    application_at = f"{year}-01-01" if '상반기' in year_half else f"{year}-07-01"

            applicant_specs = [spec.strip() for spec in response.css('div.items span.trm span.cell::text').getall() if spec.strip()]

            essays = []
            qna_list = response.css('dl.qnaLists dt, dl.qnaLists dd')
            current_question = None
            for item in qna_list:
                if item.root.tag == 'dt':
                    current_question = item.css('span.tx::text').get("").strip()
                elif item.root.tag == 'dd' and current_question:
                    answer_with_length_info = item.css('div.tx').xpath('string(.)').get("").strip()
                    length_match = re.search(r'글자수\s*([\d,]+)자', answer_with_length_info)
                    current_length = int(length_match.group(1).replace(',', '')) if length_match else None
                    answer = re.sub(r'\s*글자수\s*[\d,]+자\s*[\d,]+Byte$', '', answer_with_length_info).strip()
                    
                    if current_question and answer:
                        essays.append({"question": current_question, "answer": answer, "maxLength": current_length})
                    current_question = None

            metadata = {"source": "jobkorea", "sourceUrl": response.url, "crawledAt": datetime.now().isoformat()}
            source_data = "" # DB 용량 관리를 위해 비활성화 (필요 시 response.text로 변경)

            cover_letter_item = JobkoreaCoverLetter(
                status="accepted", companyName=company_name, positionName=position_name,
                applicationAt=application_at, applicant=applicant_specs, essays=essays,
                metadata=metadata, sourceData=source_data
            )
            cover_letter_item._validate()
            yield cover_letter_item
            
        except Exception as e:
            self.logger.error(f"An unexpected error occurred during parsing {response.url}. Error: {e}")