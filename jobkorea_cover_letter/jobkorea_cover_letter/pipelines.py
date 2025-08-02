import pymongo
from itemadapter import ItemAdapter
from datetime import datetime

class MongoPipeline:
    def __init__(self, mongo_uri, mongo_db, collection_name, log_collection_name):
        self.mongo_uri = mongo_uri
        self.mongo_db = mongo_db
        self.collection_name = collection_name
        self.log_collection_name = log_collection_name

    @classmethod
    def from_crawler(cls, crawler):
        return cls(
            mongo_uri=crawler.settings.get('MONGO_URI'),
            mongo_db=crawler.settings.get('MONGO_DATABASE'),
            collection_name=crawler.settings.get('MONGO_COLLECTION', 'cover_letters'),
            log_collection_name=crawler.settings.get('MONGO_LOG_COLLECTION', 'master_crawler_logs')
        )

    def open_spider(self, spider):
        self.client = pymongo.MongoClient(self.mongo_uri)
        self.db = self.client[self.mongo_db]
        self.collection = self.db[self.collection_name]
        self.log_collection = self.db[self.log_collection_name]
        spider.logger.info("MongoDB connection opened.")

    def close_spider(self, spider):
        self.client.close()
        spider.logger.info("MongoDB connection closed.")

    def process_item(self, item, spider):
        data = item.to_dict()
        source_url = data['metadata']['sourceUrl']
        
        try:
            # 1. 자소서 데이터 저장 (upsert)
            self.collection.update_one(
                {'metadata.sourceUrl': source_url},
                {'$set': data},
                upsert=True
            )
            
            # 2. 크롤링 성공 로그 기록 (새로운 스키마 적용)
            self.log_collection.update_one(
                {'url': source_url},
                {
                    '$addToSet': {'purposes': 'cover_letter'}, # "purposes" 배열에 목적 추가
                    '$set': {'crawledAt': datetime.now().isoformat()} # 마지막 크롤링 시각 갱신
                },
                upsert=True
            )
            
            spider.logger.debug(f"Successfully saved item and log to MongoDB: {source_url}")
        except Exception as e:
            spider.logger.error(f"Failed to save item to MongoDB. Error: {e}")
        
        return item