import scrapy
import re
from urllib.parse import urlparse
from datetime import datetime, date


class FundsForNGOSSpider(scrapy.Spider):
    name = "fundsforngos"
    allowed_domains = ["www2.fundsforngos.org"]
    start_urls = ["https://www2.fundsforngos.org/"]

    custom_settings = {
        "AUTOTHROTTLE_ENABLED": True,
        "AUTOTHROTTLE_START_DELAY": 1,
        "AUTOTHROTTLE_MAX_DELAY": 3,
        "ROBOTSTXT_OBEY": True,
        # "JOBDIR": "jobs/fundsforngos",
    }

    # ---------------- REGEX ----------------
    ORG_PATTERNS = [
        re.compile(r"([A-Z][A-Za-z\s]+ Foundation)"),
        re.compile(r"(UNICEF\s+[A-Za-z]+)"),
        re.compile(r"\b(UNICEF|UNOPS)\b"),
        re.compile(r"(U\.S\.\s+Embassy\s+in\s+[A-Za-z\s]+)"),
        re.compile(r"(?:funded|launched|hosted) by ([A-Z][A-Za-z\s&]+)"),
    ]

    # --- Improved Money Patterns ---
    MONEY_RE = re.compile(
        r'(USD|US\$|\$|EUR|€|₹)\s?'
        r'([\d,.]+)'
        r'\s*(million|billion|thousand|m|bn)?',
        re.I
    )

    RANGE_RE = re.compile(
        r'(USD|US\$|\$)\s?([\d,.]+)\s*(million|billion|m|bn)?'
        r'\s*(?:to|-|and)\s*'
        r'(USD|US\$|\$)?\s?([\d,.]+)\s*(million|billion|m|bn)?',
        re.I
    )

    UPTO_RE = re.compile(r'up to\s*USD\s?([\d,]+)', re.I)
    SINGLE_RE = re.compile(r'(?:total|indicative|overall).*?USD\s?([\d,]+)', re.I)
    FALLBACK_RE = re.compile(r'(USD|EUR|₹|\$)\s?[\d,]+')
    DATE_RE = re.compile(r"(\d{1,2}-[A-Za-z]{3}-\d{4})")

    # ---------------- INIT ----------------
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.themes_map = self._build_keyword_map({
            "children": ["children", "adolescent", "youth", "teenage"],
            "education": ["education", "school", "learning", "training"],
            "health": ["health", "medical", "hiv", "aids"],
            "women": ["women", "girls", "gender"],
            "arts & culture": ["culture", "cultural", "heritage", "museum", "arts"],
            "community development": ["community", "livelihood", "social protection"],
            "disability": ["disability", "disabled", "assistive"],
        })

        self.countries_map = self._build_keyword_map({
            "United States": ["usa", "united states", "u.s."],
            "Canada": ["canada"],
            "Australia": ["australia"],
            "United Kingdom": ["united kingdom", "uk"],
            "India": ["india"],
            "Uganda": ["uganda"],
            "Kenya": ["kenya"],
            "Nigeria": ["nigeria"],
            "Pakistan": ["pakistan"],
            "Bangladesh": ["bangladesh"],
            "Philippines": ["philippines"],
            "South Africa": ["south africa"],
            "Thailand": ["thailand"],
            "Israel": ["israel"],
            "Hungary": ["hungary"],
            "Japan": ["japan"],
            "Finland": ["finland"],
            "Malaysia": ["malaysia"],
            "Bosnia and Herzegovina": ["bosnia", "herzegovina"],
            "Vietnam": ["vietnam"],
            "Samoa": ["samoa"],
            "South Sudan": ["south sudan"],
            "Ecuador": ["ecuador"],
            "Slovakia": ["slovakia"],
            "New Zealand": ["new zealand"],
        })

    # ---------------- UTIL ----------------
    def _build_keyword_map(self, raw):
        mapping, words = {}, []
        for k, vals in raw.items():
            for v in vals:
                v = v.lower()
                mapping[v] = k
                words.append(re.escape(v))
        return {
            "regex": re.compile(r'\b(' + '|'.join(words) + r')\b', re.I),
            "map": mapping
        }

    def extract_organization(self, text):
        for p in self.ORG_PATTERNS:
            m = p.search(text)
            if m:
                return m.group(1) if m.lastindex else m.group(0)
        return "Not specified"

    def extract_funding_amount(self, text):
        # ---- RANGE ----
        if m := self.RANGE_RE.search(text):
            start = f"{m.group(1)} {m.group(2)} {m.group(3) or ''}".strip()
            end = f"{m.group(4) or m.group(1)} {m.group(5)} {m.group(6) or ''}".strip()
            return f"{start} – {end}"

        # ---- SINGLE AMOUNT ----
        matches = list(self.UPTO_RE.finditer(text))
        if not matches:
            matches = list(self.SINGLE_RE.finditer(text))
        if not matches:
            matches = list(self.FALLBACK_RE.finditer(text))

        if matches:
            # Pick the largest realistic amount (usually the main grant)
            best = matches[0]
            if hasattr(best, 'group'):
                amount = best.group(0)
                return amount.strip()

        return None


    def extract_country(self, title, text):
        # 1️⃣ Exact country in title parentheses
        if m := re.search(r"\(([^)]+)\)", title):
            cand = m.group(1).strip().lower()
            for c in self.countries_map["map"].values():
                if cand == c.lower():
                    return c

        # 2️⃣ Keyword search
        combined = f"{title} {text}".lower()
        if m := self.countries_map["regex"].search(combined):
            return self.countries_map["map"][m.group(1).lower()]

        return "Global"

    def extract_category_fast(self, text, map_obj):
        if m := map_obj["regex"].search(text):
            return map_obj["map"][m.group(1).lower()]
        return "General"

    # ---------------- PARSE ----------------
    def parse(self, response):
        # Assuming this is the method with indentation issues
        text = response.text  # Define text if it was undefined
        for post in response.css("article"):
            title = post.css("a.entry-title-link::text").get("")
            url = post.css("a.entry-title-link::attr(href)").get()
            if url:
                yield response.follow(url, self.parse_detail, cb_kwargs={"title": title})

        if next_page := response.css("li.pagination-next a::attr(href)").get():
            yield response.follow(next_page, self.parse)

    def parse_detail(self, response, title):
        text_blob = " ".join(response.xpath('//article//p//text()').getall())
        clean_text = re.sub(r"\s+", " ", text_blob).strip()

        # ---- DEADLINE ----
        deadline_text = " ".join(
            response.xpath(
                '//p[.//strong[contains(text(),"Deadline")] or contains(text(),"Deadline")]//text()'
            ).getall()
        )
        deadline_text = re.sub(r"\s+", " ", deadline_text).strip()

        deadline = None
        if m := self.DATE_RE.search(deadline_text):
            deadline = m.group(1)
            if datetime.strptime(deadline, "%d-%b-%Y").date() < date.today():
                return  # ❌ expired

        # ---- FUNDING (REQUIRED) ----
        funding = self.extract_funding_amount(clean_text)
        if not funding:
            return  # ❌ reject if no amount

        # ---- DESCRIPTION ----
        description = None
        for p in response.xpath('//article//p/text()').getall():
            p = p.strip()
            if len(p) > 50 and "deadline" not in p.lower():
                description = p
                break

        # ---- THEME ----
        full_context = f"{title} {clean_text}"
        path = urlparse(response.url).path.lower()
        theme = "General"
        for t in self.themes_map["map"].values():
            if t.replace(" ", "-") in path:
                theme = t
                break
        if theme == "General":
            theme = self.extract_category_fast(full_context, self.themes_map)

        yield {
            "Title": title,
            "Organization": self.extract_organization(clean_text),
            "Funding Amount": funding,
            "Thematic Area": theme,
            "Country": self.extract_country(title, clean_text),
            "Description": description,
            "Deadline": deadline,
            "Source URL": response.url,
        }
