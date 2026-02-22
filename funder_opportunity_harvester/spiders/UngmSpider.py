import scrapy
import json

class UngmSpider(scrapy.Spider):
    name = "ungm"
    allowed_domains = ["ungm.org"]
    search_url = "https://www.ungm.org/Public/Notice/Search"

    headers = {
        "Content-Type": "application/json",
        "X-Requested-With": "XMLHttpRequest",
        "Origin": "https://www.ungm.org",
        "Referer": "https://www.ungm.org/Public/Notice",
        "User-Agent": "Mozilla/5.0"
    }

    def start_requests(self):
        yield self.make_request(page=0)

    def make_request(self, page):
        payload = {
            "PageIndex": page,
            "PageSize": 15,
            "Title": "",
            "Description": "",
            "Reference": "",
            "PublishedFrom": "",
            "PublishedTo": "20-Feb-2026",
            "DeadlineFrom": "20-Feb-2026",
            "DeadlineTo": "",
            "Agencies": [],
            "Countries": [],
            "UNSPSCs": [],
            "TypeOfCompetitions": [],
            "NoticeTypes": [],
            "IsActive": True,
            "IsSustainable": False,
            "NoticeDisplayType": None,
            "SortField": "Deadline",
            "SortAscending": True,
            "NoticeSearchTotalLabelId": "noticeSearchTotal",
            "IsPicker": False
        }

        return scrapy.Request(
            self.search_url,
            method="POST",
            headers=self.headers,
            body=json.dumps(payload),
            callback=self.parse,
            meta={"page": page}
        )

    def parse(self, response):
        page = response.meta["page"]

        rows = response.css("div.tableRow.notice-table")

        if not rows:
            return

        for row in rows:
            yield {
                "notice_id": row.attrib.get("data-noticeid"),
                "title": row.css(".resultTitle .ungm-title::text").get(),
                "deadline": row.css(".deadline span::text").get(),
                "agency": row.css(".resultAgency span::text").get(),
                "reference": row.css(".resultInfo1 span::text").get(),
                "country": row.css("div.tableCell:nth-child(8) span::text").get(),
                "detail_url": response.urljoin(
                    row.css(".resultTitle a::attr(href)").get()
                )
            }

        # pagination
        next_page = page + 1
        yield self.make_request(next_page)
