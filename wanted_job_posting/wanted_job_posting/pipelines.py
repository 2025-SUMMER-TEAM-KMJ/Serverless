import pymongo
from datetime import datetime

from wanted_job_posting.models import MasterJobPosting, WantedJobPosting

class WantedJobPostingPipeline:
    """
    오직 WantedJobPosting 아이템만 처리하여 MongoDB에 저장하는 파이프라인.
    """
    collection_name = 'wanted_job_postings' # 저장할 컬렉션 이름
    log_collection_name = 'master_crawler_logs'

    @classmethod
    def from_crawler(cls, crawler):
        return cls(mongo_uri=crawler.settings.get('MONGO_URI'), mongo_db=crawler.settings.get('MONGO_DATABASE'))

    def __init__(self, mongo_uri, mongo_db):
        print(mongo_uri, mongo_db)
        self.mongo_uri = mongo_uri
        self.mongo_db = mongo_db

    def open_spider(self, spider):
        self.client = pymongo.MongoClient(self.mongo_uri)
        self.db = self.client[self.mongo_db]
        self.collection = self.db[self.collection_name]
        self.log_collection = self.db[self.log_collection_name]

    def close_spider(self, spider):
        self.client.close()

    def process_item(self, item, spider):
        # 이 파이프라인은 WantedJobPosting이 아니면 아무 작업도 하지 않고 그냥 통과시킴
        if not isinstance(item, WantedJobPosting):
            return item

        data = item.to_dict()
        source_url = data.get('metadata', {}).get('sourceUrl')

        self.collection.update_one({'metadata.sourceUrl': source_url}, {'$set': data}, upsert=True)

        self.log_collection.update_one(
            {'url': source_url},
            {
                '$addToSet': {'purposes': 'job_posting'}, # "purposes" 배열에 목적 추가
                '$set': {'crawledAt': datetime.now().isoformat()} # 마지막 크롤링 시각 갱신
            },
            upsert=True
        )
        spider.logger.debug(f"WantedJobPosting saved to DB: {source_url}")
        return item


class MasterJobPostingPipeline:
    """
    오직 MasterJobPosting 아이템만 처리하여 저장하고, 로그까지 기록하는 파이프라인.
    """
    collection_name = 'master_job_postings'
    log_collection_name = 'master_crawler_logs'

    @classmethod
    def from_crawler(cls, crawler):
        return cls(mongo_uri=crawler.settings.get('MONGO_URI'), mongo_db=crawler.settings.get('MONGO_DATABASE'))

    def __init__(self, mongo_uri, mongo_db):
        self.mongo_uri = mongo_uri
        self.mongo_db = mongo_db

    def open_spider(self, spider):
        self.client = pymongo.MongoClient(self.mongo_uri)
        self.db = self.client[self.mongo_db]
        self.collection = self.db[self.collection_name]
        self.log_collection = self.db[self.log_collection_name]

    def close_spider(self, spider):
        self.client.close()

    def process_item(self, item, spider):
        # 이 파이프라인은 MasterJobPosting이 아니면 아무 작업도 하지 않고 그냥 통과시킴
        if not isinstance(item, MasterJobPosting):
            return item
            
        data = item.to_dict()
        source_url = data.get('metadata', {}).get('sourceUrl')
        
        # 1. 데이터 저장
        self.collection.update_one({'metadata.sourceUrl': source_url}, {'$set': data}, upsert=True)
        
        # 2. 로그 기록
        self.log_collection.update_one(
            {'url': source_url},
            {
                '$addToSet': {'purposes': 'job_posting'}, # "purposes" 배열에 목적 추가
                '$set': {'crawledAt': datetime.now().isoformat()} # 마지막 크롤링 시각 갱신
            },
            upsert=True
        )
        spider.logger.info(f"MasterJobPosting and log saved to DB: {source_url}")
        return item