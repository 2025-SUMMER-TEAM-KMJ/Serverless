import os
from dotenv import load_dotenv

# GitHub Actions 환경인지 확인 (CI 환경 변수는 대부분의 CI/CD 플랫폼에서 true로 설정됨)
# GitHub Actions는 'CI'와 'GITHUB_ACTIONS' 환경 변수를 모두 true로 설정합니다.
IS_GITHUB_ACTIONS = os.getenv('GITHUB_ACTIONS') == 'true'

# 로컬 환경일 경우에만 .env 파일을 로드합니다.
if not IS_GITHUB_ACTIONS:
    dotenv_path = os.path.join(os.path.dirname(__file__), '..', '..', '.env')
    if os.path.exists(dotenv_path):
        print("Loading .env file for local development.")
        load_dotenv(dotenv_path)
    else:
        print("Warning: .env file not found. Falling back to environment variables or defaults.")
else:
    print("Running in GitHub Actions environment. Using secrets as environment variables.")

# Scrapy settings for wanted_job_posting project
#
# For simplicity, this file contains only settings considered important or
# commonly used. You can find more settings consulting the documentation:
#
#     https://docs.scrapy.org/en/latest/topics/settings.html
#     https://docs.scrapy.org/en/latest/topics/downloader-middleware.html
#     https://docs.scrapy.org/en/latest/topics/spider-middleware.html

BOT_NAME = "wanted_job_posting"

SPIDER_MODULES = ["wanted_job_posting.spiders"]
NEWSPIDER_MODULE = "wanted_job_posting.spiders"

ADDONS = {}


# Crawl responsibly by identifying yourself (and your website) on the user-agent
#USER_AGENT = "wanted_job_posting (+http://www.yourdomain.com)"

# Obey robots.txt rules
# ROBOTSTXT_OBEY = True
ROBOTSTXT_OBEY = False

# 방금 작성한 MongoDB 파이프라인 활성화
ITEM_PIPELINES = {
   'wanted_job_posting.pipelines.MongoPipeline': 300,
}

# MongoDB 연결 정보 (사용자 환경에 맞게 수정)
MONGO_URI = os.getenv('MONGO_URI', 'mongodb://localhost:27017/')
MONGO_DATABASE = os.getenv('MONGO_DATABASE', 'wanted_db')
MONGO_COLLECTION = os.getenv('MONGO_COLLECTION', 'wanted_job_postings')
MONGO_LOG_COLLECTION = os.getenv('MONGO_LOG_COLLECTION', 'master_crawler_logs')

# Concurrency and throttling settings
#CONCURRENT_REQUESTS = 16
CONCURRENT_REQUESTS_PER_DOMAIN = 1
DOWNLOAD_DELAY = 1

# Disable cookies (enabled by default)
#COOKIES_ENABLED = False

# Disable Telnet Console (enabled by default)
TELNETCONSOLE_ENABLED = False

# Override the default request headers:
#DEFAULT_REQUEST_HEADERS = {
#    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
#    "Accept-Language": "en",
#}

# Enable or disable spider middlewares
# See https://docs.scrapy.org/en/latest/topics/spider-middleware.html
#SPIDER_MIDDLEWARES = {
#    "wanted_job_posting.middlewares.WantedJobPostingSpiderMiddleware": 543,
#}

# Enable or disable downloader middlewares
# See https://docs.scrapy.org/en/latest/topics/downloader-middleware.html
#DOWNLOADER_MIDDLEWARES = {
#    "wanted_job_posting.middlewares.WantedJobPostingDownloaderMiddleware": 543,
#}

# Enable or disable extensions
# See https://docs.scrapy.org/en/latest/topics/extensions.html
#EXTENSIONS = {
#    "scrapy.extensions.telnet.TelnetConsole": None,
#}

# Configure item pipelines
# See https://docs.scrapy.org/en/latest/topics/item-pipeline.html
#ITEM_PIPELINES = {
#    "wanted_job_posting.pipelines.WantedJobPostingPipeline": 300,
#}

# Enable and configure the AutoThrottle extension (disabled by default)
# See https://docs.scrapy.org/en/latest/topics/autothrottle.html
#AUTOTHROTTLE_ENABLED = True
# The initial download delay
#AUTOTHROTTLE_START_DELAY = 5
# The maximum download delay to be set in case of high latencies
#AUTOTHROTTLE_MAX_DELAY = 60
# The average number of requests Scrapy should be sending in parallel to
# each remote server
#AUTOTHROTTLE_TARGET_CONCURRENCY = 1.0
# Enable showing throttling stats for every response received:
#AUTOTHROTTLE_DEBUG = False

# Enable and configure HTTP caching (disabled by default)
# See https://docs.scrapy.org/en/latest/topics/downloader-middleware.html#httpcache-middleware-settings
#HTTPCACHE_ENABLED = True
#HTTPCACHE_EXPIRATION_SECS = 0
#HTTPCACHE_DIR = "httpcache"
#HTTPCACHE_IGNORE_HTTP_CODES = []
#HTTPCACHE_STORAGE = "scrapy.extensions.httpcache.FilesystemCacheStorage"

# Set settings whose default value is deprecated to a future-proof value
FEED_EXPORT_ENCODING = "utf-8"