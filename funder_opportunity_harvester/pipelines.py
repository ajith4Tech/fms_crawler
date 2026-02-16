import os
import requests
from itemadapter import ItemAdapter


class FrappePipeline:

    def open_spider(self, spider):
        self.endpoint = os.getenv(
            "FRAPPE_ENDPOINT",
            "http://localhost:8000/api/method/scrapy.api.upsert"
        )

        self.headers = {
            "Authorization": "token 13d3a01364934a5:fef5d311c877c41",
            "Content-Type": "application/json"
        }

        spider.logger.info("FrappePipeline initialized successfully")

    def process_item(self, item, spider):
        adapter = ItemAdapter(item)

        # Transform spider fields → Frappe schema
        transformed = {
            "title": adapter.get("Title"),
            "organization": adapter.get("Organization"),
            "funding_amount": adapter.get("Funding Amount"),
            "thematic_area": adapter.get("Thematic Area"),
            "description": adapter.get("Description"),
            "source_url": adapter.get("Source URL"),
            "country": adapter.get("Country"),
            "deadline": adapter.get("Deadline"),
        }

        # Validate required fields
        if not transformed["title"] or not transformed["organization"]:
            spider.logger.warning(
                f"Skipping item due to missing title/org: {transformed}"
            )
            return item

        try:
            response = requests.post(
                self.endpoint,
                json=transformed,
                headers=self.headers,
                timeout=10
            )

            if response.status_code != 200:
                spider.logger.error(
                    f"Frappe API error {response.status_code}: {response.text}"
                )

        except requests.exceptions.Timeout:
            spider.logger.error("Frappe API request timed out")

        except requests.exceptions.ConnectionError:
            spider.logger.error("Frappe API connection error")

        except Exception as e:
            spider.logger.error(f"Unexpected error sending to Frappe: {e}")

        return item
