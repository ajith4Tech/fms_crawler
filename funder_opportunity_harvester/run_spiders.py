import sys
import os

# Ensure the parent directory is on sys.path so the package is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings

from funder_opportunity_harvester.spiders.fundsforngos import FundsForNGOSSpider
from funder_opportunity_harvester.spiders.UngmSpider import UngmSpider
from funder_opportunity_harvester.spiders.ngobox import NgoBoxSpider

process = CrawlerProcess(get_project_settings())

process.crawl(FundsForNGOSSpider)
process.crawl(UngmSpider)
process.crawl(NgoBoxSpider)

process.start()
