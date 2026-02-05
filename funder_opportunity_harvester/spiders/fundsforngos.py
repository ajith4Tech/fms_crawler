import scrapy


class FundsforngosSpider(scrapy.Spider):
    name = "fundsforngos"
    allowed_domains = ["fundsforngos.org"]
    start_urls = ["https://fundsforngos.org"]

    def parse(self, response):
        pass
