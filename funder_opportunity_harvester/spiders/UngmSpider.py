import scrapy
import json
import re
from datetime import datetime


class UngmSpider(scrapy.Spider):
    name = "ungm"
    allowed_domains = ["ungm.org"]
    search_url = "https://www.ungm.org/Public/Notice/Search"

    headers = {
        "Content-Type": "application/json",
        "X-Requested-With": "XMLHttpRequest",
        "Origin": "https://www.ungm.org",
        "Referer": "https://www.ungm.org/Public/Notice",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    }

    # Map UNGM notice type / category keywords → Thematic Area
    THEME_MAP = {
        "health": "health",
        "medical": "health",
        "education": "education",
        "environment": "environment",
        "climate": "environment",
        "water": "water & sanitation",
        "sanitation": "water & sanitation",
        "food": "food security",
        "agriculture": "food security",
        "technology": "information technology",
        "it ": "information technology",
        "digital": "information technology",
        "gender": "gender",
        "women": "gender",
        "child": "children",
        "youth": "children",
        "community": "community development",
        "peace": "peace & security",
        "humanitar": "humanitarian",
        "transport": "infrastructure",
        "infrastructure": "infrastructure",
        "energy": "energy",
        "finance": "finance",
    }

    def start_requests(self):
        yield self._make_search_request(page=0)

    def _make_search_request(self, page):
        today = datetime.today().strftime("%d-%b-%Y")
        payload = {
            "PageIndex": page,
            "PageSize": 15,
            "Title": "",
            "Description": "",
            "Reference": "",
            "PublishedFrom": "",
            "PublishedTo": "",
            "DeadlineFrom": today,
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
            "IsPicker": False,
        }
        return scrapy.Request(
            self.search_url,
            method="POST",
            headers=self.headers,
            body=json.dumps(payload),
            callback=self._parse_listing,
            meta={"page": page},
        )

    def _parse_listing(self, response):
        page = response.meta["page"]
        rows = response.css("div.tableRow.notice-table")

        if not rows:
            return  # No more results – stop pagination

        for row in rows:
            detail_path = row.css(".resultTitle a::attr(href)").get()
            if not detail_path:
                continue

            detail_url = response.urljoin(detail_path)
            deadline_raw = row.css(".deadline span::text").get("").strip()

            yield scrapy.Request(
                detail_url,
                headers={
                    "User-Agent": self.headers["User-Agent"],
                    "Referer": "https://www.ungm.org/Public/Notice",
                },
                callback=self._parse_detail,
                meta={
                    "deadline_raw": deadline_raw,
                    "detail_url": detail_url,
                },
            )

        # Paginate
        yield self._make_search_request(page + 1)

    def _parse_detail(self, response):
        deadline_raw = response.meta["deadline_raw"]
        detail_url = response.meta["detail_url"]

        # ── Title ──────────────────────────────────────────────────────────
        title = self._clean_text(
            response.css("h1.title::text, h2.title::text, .notice-title::text").get("")
            or response.css("h1::text").get("")
        )

        # ── Organization (issuing UN agency) ──────────────────────────────
        organization = self._clean_text(
            response.css(".field-label:contains('Organization') + .field-items span::text").get("")
            or response.css("span.ungm-agency::text").get("")
            or response.css("td:contains('Organization') + td::text").get("")
            or self._extract_labeled("Organization", response)
            or self._extract_labeled("Agency", response)
            or "United Nations"
        )

        # ── Country ───────────────────────────────────────────────────────
        country = (
            response.xpath(
                "//dt[contains(normalize-space(.), 'Country')]/following-sibling::dd[1]//text()"
            ).get()
            or response.xpath(
                "//td[contains(normalize-space(.), 'Country')]/following-sibling::td[1]//text()"
            ).get()
            or ""
        )
        country = re.sub(r"\s+", " ", country or "").strip()
        if not country:
            country = "Global"

        # ── Description ───────────────────────────────────────────────────
        # Stronger extraction from noticeDetail div, avoiding script tags
        desc_parts = response.xpath(
            "//div[@id='noticeDetail']//text()[not(ancestor::script)]"
        ).getall()
        
        if not desc_parts:
            # Fallback to original selectors
            desc_parts = response.css(
                ".notice-description p::text, "
                "#noticeDescription p::text, "
                ".field-description p::text, "
                ".description p::text"
            ).getall()
        
        description = " ".join(p.strip() for p in desc_parts if p.strip())
        if not description:
            # Second fallback: grab all visible text in description block
            description = " ".join(
                response.css(
                    ".notice-description ::text, #noticeDescription ::text"
                ).getall()
            ).strip()
        
        description = self._clean_text(description)[:600]

        # ── Funding Amount ─────────────────────────────────────────────────
        funding_amount = self._clean_text(
            self._extract_labeled("Estimated Value", response)
            or self._extract_labeled("Contract Value", response)
            or self._extract_labeled("Budget", response)
            or "Not specified"
        )

        # ── Thematic Area ─────────────────────────────────────────────────
        thematic_area = self._infer_theme(title + " " + description)

        # ── Deadline ──────────────────────────────────────────────────────
        deadline = self._format_deadline(deadline_raw)
        if not deadline:
            deadline = self._clean_text(
                self._extract_labeled("Deadline", response)
                or self._extract_labeled("Closing Date", response)
                or ""
            )

        # Apply final fallbacks for required fields
        yield {
            "Title": title or "Not specified",
            "Organization": organization or "United Nations",
            "Funding Amount": funding_amount or "Not specified",
            "Thematic Area": thematic_area,
            "Country": country,
            "Description": description or "Not specified",
            "Deadline": deadline,
            "Source URL": detail_url,
        }

    # ── Helpers ────────────────────────────────────────────────────────────

    def _clean_text(self, text):
        """Remove extra whitespace, newlines, and normalize spaces."""
        if not text:
            return ""
        return re.sub(r"\s+", " ", text).strip()

    def _extract_labeled(self, label, response):
        """Generic label→value extractor for definition-list / table patterns."""
        # dt/dd pattern
        value = response.xpath(
            f"//dt[contains(normalize-space(.), '{label}')]/following-sibling::dd[1]//text()"
        ).getall()
        if value:
            return " ".join(v.strip() for v in value if v.strip())

        # th/td pattern
        value = response.xpath(
            f"//td[contains(normalize-space(.), '{label}')]/following-sibling::td[1]//text()"
        ).getall()
        if value:
            return " ".join(v.strip() for v in value if v.strip())

        # label: value inline (strict pattern to avoid footer/JS matches)
        value = response.xpath(
            f"//*[contains(text(), '{label}:')]/following-sibling::*[1]//text()"
        ).getall()
        if value:
            return " ".join(v.strip() for v in value if v.strip())

        return ""

    def _infer_theme(self, text):
        """Infer thematic area from title and description text."""
        text_lower = text.lower()
        for keyword, theme in self.THEME_MAP.items():
            if keyword in text_lower:
                return theme
        return "General"

    def _format_deadline(self, raw):
        """Clean and normalize deadline text, removing timezone and extra whitespace."""
        if not raw:
            return ""
        
        # Remove extra whitespace and newlines
        raw = re.sub(r"\s+", " ", raw).strip()

        # Extract date + time only (ignore GMT part)
        match = re.search(r"\d{2}-\w{3}-\d{4}\s\d{2}:\d{2}", raw)
        if match:
            return match.group(0)

        return raw  # Return as-is if no format matched