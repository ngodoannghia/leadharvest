"""
Scrapy settings for leadharvest project.
"""

BOT_NAME = "leadharvest"

SPIDER_MODULES = ["leadharvest.spiders"]
NEWSPIDER_MODULE = "leadharvest.spiders"

# Tuân thủ nguyên tắc cào B2B có trách nhiệm
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
ROBOTSTXT_OBEY = False

# Giới hạn tốc độ để không làm quá tải server nguồn (BA §13.2)
CONCURRENT_REQUESTS = 8
CONCURRENT_REQUESTS_PER_DOMAIN = 4
DOWNLOAD_DELAY = 0.5

# Encoding & logging
FEED_EXPORT_ENCODING = "utf-8"
LOG_LEVEL = "INFO"

# Pipeline lưu dữ liệu thô phục vụ 2-phase build
ITEM_PIPELINES = {
    "leadharvest.pipelines.RawLeadStoragePipeline": 300,
}
