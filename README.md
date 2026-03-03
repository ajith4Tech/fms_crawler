# fms_crawler

A [Scrapy](https://scrapy.org/) project that harvests funding opportunities from multiple sources and pushes them into a Frappe backend via REST API.

---

## Project Structure

```
fms_crawler/
├── scrapy.cfg
└── funder_opportunity_harvester/
    ├── settings.py          # Scrapy project settings
    ├── items.py             # Item definitions
    ├── pipelines.py         # FrappePipeline – sends scraped data to Frappe
    ├── middlewares.py       # Spider & downloader middlewares
    └── spiders/
        ├── fundsforngos.py  # Spider for fundsforngos.org
        └── UngmSpider.py    # Spider for ungm.org (UN procurement notices)
```

---

## Spiders

### `fundsforngos` — [fundsforngos.org](https://www2.fundsforngos.org/)

Crawls the FundsForNGOs website and extracts active grant opportunities.

**Extracted fields:**

| Field | Description |
|---|---|
| `Title` | Grant title |
| `Organization` | Funding organisation (regex-extracted) |
| `Funding Amount` | Grant amount or range (multi-currency, supports Indian scales) |
| `Thematic Area` | Theme (e.g. education, health, women) |
| `Country` | Target country or "Global" |
| `Description` | First meaningful paragraph |
| `Deadline` | Application deadline (skips expired opportunities) |
| `Source URL` | Link to the original post |

**Features:**
- Auto-throttle enabled (1–3 s delay) to crawl politely.
- Skips opportunities with no funding amount or a past deadline.
- Regex-based extraction for organisations, currencies, and dates.

---

### `ungm` — [ungm.org](https://www.ungm.org/Public/Notice)

Crawls the UN Global Marketplace and extracts active procurement notices via its internal JSON search API.

**Extracted fields:**

| Field | Description |
|---|---|
| `notice_id` | Unique UNGM notice ID |
| `title` | Notice title |
| `deadline` | Application deadline |
| `agency` | Issuing UN agency |
| `reference` | Notice reference number |
| `country` | Country of interest |
| `detail_url` | Full URL to the notice detail page |

**Features:**
- Uses a **POST**-based JSON search API (`/Public/Notice/Search`) instead of HTML pagination.
- Automatically paginates through all results (15 per page) until no more rows are returned.
- Filters to active notices (`IsActive: true`) with a future deadline.
- Sorted by deadline ascending so the soonest-closing opportunities appear first.

---

### `ngobox` — [ngobox.org](https://ngobox.org/grant_announcement_listing.php)

Crawls ngobox.org for active grant and funding announcements. 

**Extracted fields:**

| Field | Description |
|---|---|
| `Title` | Grant title |
| `Organization` | Funding organisation |
| `Funding Amount` | Grant amount or range |
| `Thematic Area` | Theme (extracted from 'Focus areas' block) |
| `Country` | Target country or location |
| `Description` | Combined text blocks describing the opportunity |
| `Deadline` | Application deadline (normalized to YYYY-MM-DD) |
| `Source URL` | Link to the original post |

**Features:**
- Paginates via standard link following.
- Fetches detailed content via a separate detail page request.
- Uses regex to meticulously extract thematic areas from 'Focus areas/Eligibility' text blocks.
- Uses regex to strictly match country or location.
- Automatically normalizes the deadline to standard ISO date format (`YYYY-MM-DD`).

---

## Pipeline — `FrappePipeline`

After scraping, every item is **POST**ed to a Frappe endpoint:

```
POST http://localhost:8000/api/method/scrapy.api.upsert
```

Configure the endpoint and credentials via environment variables:

| Variable | Default | Description |
|---|---|---|
| `FRAPPE_ENDPOINT` | `http://localhost:8000/api/method/scrapy.api.upsert` | Frappe API URL |

The Authorization token is set in `pipelines.py`. Update it to match your Frappe API key.

Items missing a `title` or `organization` are skipped automatically.

---

## Requirements

- Python 3.10+
- Scrapy
- requests
- itemadapter

Install dependencies:

```bash
pip install scrapy requests itemadapter
```

---

## Configuration

Key settings in `funder_opportunity_harvester/settings.py`:

| Setting | Value | Notes |
|---|---|---|
| `USER_AGENT` | Chrome 120 UA string | Mimics a real browser |
| `ROBOTSTXT_OBEY` | `False` | Overridden per spider where needed |
| `CONCURRENT_REQUESTS_PER_DOMAIN` | `1` | Polite single-threaded crawl |
| `DOWNLOAD_DELAY` | `2` | 2 s delay between requests |
| `COOKIES_ENABLED` | `False` | Cookies disabled globally |

---

## Usage

Run all spiders concurrently:

```bash
python3 funder_opportunity_harvester/run_spiders.py
```

Run a specific spider:

```bash
scrapy crawl fundsforngos
scrapy crawl ungm
scrapy crawl ngobox
```

Export to a JSON file instead of the Frappe pipeline:

```bash
scrapy crawl fundsforngos -o opportunities.json
scrapy crawl ungm -o ungm_notices.json
scrapy crawl ngobox -o ngobox.json
```

Override the Frappe endpoint at runtime:

```bash
FRAPPE_ENDPOINT=https://your-frappe-site/api/method/scrapy.api.upsert scrapy crawl fundsforngos
FRAPPE_ENDPOINT=https://your-frappe-site/api/method/scrapy.api.upsert scrapy crawl ungm
FRAPPE_ENDPOINT=https://your-frappe-site/api/method/scrapy.api.upsert scrapy crawl ngobox
```

---
