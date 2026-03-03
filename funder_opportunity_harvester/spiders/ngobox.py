import scrapy
from urllib.parse import urljoin
import re
from datetime import datetime


class NgoBoxSpider(scrapy.Spider):
    name = "ngobox"
    allowed_domains = ["ngobox.org"]
    start_urls = ["https://ngobox.org/grant_announcement_listing.php"]

    def parse(self, response):

        cards = response.css("div.card")

        for card in cards:

            title = card.css("a.card-title::text").get()
            if title:
                title = title.strip()

            relative_url = card.css("a.card-title::attr(href)").get()
            if not relative_url:
                continue

            source_url = urljoin(response.url, relative_url)

            organization = card.css("p.p_balck::text").get()
            if organization:
                organization = organization.strip()

            funding_amount = card.css("p.card-text2::text").get()
            if funding_amount:
                funding_amount = funding_amount.replace("Grant Amount:", "").strip()

            deadline_raw = card.css("div.list_bottumsec::text").re_first(
                r"\d{1,2}\s\w+\.\s\d{4}"
            )

            deadline = self.normalize_date(deadline_raw)

            yield response.follow(
                source_url,
                callback=self.parse_detail,
                meta={
                    "Title": title,
                    "Organization": organization,
                    "Funding Amount": funding_amount,
                    "Deadline": deadline,
                    "Source URL": source_url,
                },
            )

        # -------- FIXED PAGINATION --------
        page_links = response.css("#feature_pagination a::attr(href)").getall()

        for link in page_links:
            yield response.follow(link, callback=self.parse)

    # -------------------------------------
    # DETAIL PAGE
    # -------------------------------------
    def parse_detail(self, response):

        content_block = response.css("div.row.row_section.font_chance12")

        description_parts = content_block.css("p ::text, li ::text").getall()
        description = " ".join(
            text.strip() for text in description_parts if text.strip()
        )

        description = re.sub(r"\s+", " ", description).strip()

        thematic_area = self.extract_thematic_area(description)
        country = self.extract_country(description)

        yield {
            "Title": response.meta["Title"],
            "Organization": response.meta["Organization"],
            "Funding Amount": response.meta["Funding Amount"],
            "Thematic Area": thematic_area,
            "Country": country,
            "Description": description,
            "Deadline": response.meta["Deadline"],
            "Source URL": response.meta["Source URL"],
        }

    # -------------------------------------
    # THEMATIC AREA FROM FOCUS BLOCK
    # -------------------------------------
    def extract_thematic_area(self, description):

        focus_match = re.search(
            r"Focus areas(.*?)(Eligibility|How to Apply)",
            description,
            re.IGNORECASE | re.DOTALL
        )

        if focus_match:
            focus_text = focus_match.group(1)
            matches = re.findall(r"\b([A-Z][a-zA-Z\s]+):", focus_text)

            if matches:
                return ", ".join(set(matches))

        return None

    # -------------------------------------
    # STRICT COUNTRY EXTRACTION
    # -------------------------------------
    def extract_country(self, description):

        country_match = re.search(
            r"(?:Country|Location)\s*:\s*([A-Za-z ,]+)",
            description,
            re.IGNORECASE
        )

        if country_match:
            return country_match.group(1).strip()

        return None

    # -------------------------------------
    # DATE NORMALIZER
    # -------------------------------------
    def normalize_date(self, date_string):
        if not date_string:
            return None

        try:
            parsed_date = datetime.strptime(date_string, "%d %b. %Y")
            return parsed_date.strftime("%Y-%m-%d")
        except Exception:
            return date_string