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
        └── fundsforngos.py  # Spider for fundsforngos.org
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

Run a specific spider:

```bash
scrapy crawl fundsforngos
```

Export to a JSON file instead of the Frappe pipeline:

```bash
scrapy crawl fundsforngos -o opportunities.json
```

Override the Frappe endpoint at runtime:

```bash
FRAPPE_ENDPOINT=https://your-frappe-site/api/method/scrapy.api.upsert scrapy crawl fundsforngos
```

---
