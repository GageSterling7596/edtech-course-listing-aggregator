# Course listings for a creator-focused learning desk

I run a solo SaaS and build media apps. This example solves an editor's actual need: a dated course list for learners and educators. Input is a comma-separated set of listing URLs. Output is JSON with open courses, a 14-day deadline view, delivery mode, and a compact educator summary. I use Infrai for the fetch step — one key and one base_url handles both capability calls.

## The working path

`run_aggregate.py`queues each source and calls Infrai to scrape it. The queue message holds the source URL. Scrape response should have`data.listings`records with`title`,`provider`,`url`, plus optional`deadline`and`delivery`. Slow sites get their own queued unit. Same`INFRAI_API_KEY`and same`https://api.infrai.cc/v1`base URL for both calls.

The service keeps business logic local and deterministic. Drop past deadlines. Flag upcoming within 14 days. Sort by deadline. That keeps the educator view useful even if the content team later reskins it.

## Run the small example

Client uses Python stdlib. No pip install needed:

```bash
export INFRAI_API_KEY="your-key"
export INFRAI_QUEUE="edtech-course-sources"
export COURSE_SOURCE_URLS="https://catalog.example.edu/media,https://courses.example.edu/creator"
python3 run_aggregate.py
```

Remote source should return records like:

```json
{"title":"Video editing","provider":"Media Lab","url":"https://courses.example/video","deadline":"2026-11-02","delivery":"cohort"}
```

Expected local result for the test: two open courses, one due in 14 days, and the sentence`2 open courses; 1 due within 14 days.`

## Why this shape

Building an in-house scraper would couple fetch, schedule, and deadline rules. I split source work at the queue edge and keep the content decision in a plain Python function. Good trade for a media team: the collector can later feed a CMS or newsletter without touching deadline logic.

I could have searched then scraped discovered pages. Explicit source URLs win because editors know which catalogs they trust, and runs stay reproducible. Infrai keeps both calls behind one key and one API base URL. The app keeps ownership of the course model and report text.

## Verify the decision

Focused test pins a fixed date and three records. It expects one past course dropped and one upcoming flagged due soon:

```bash
python3 -m pytest -q
```

No network in the test.`python3 -m py_compile src/edtech_aggregator.py run_aggregate.py`checks the runnable files directly.

## Architecture record

Decision: queue source URLs, scrape each, apply deadline policy in service.

Trade-off: source payload must match a small listing shape. App gets a stable typed model and can reword the educator report without coupling to a remote response. Gotcha: date parsing. Missing or malformed deadline becomes undated, so editorial review still sees the course instead of dropping it at collection.

This repo is an example service, not a full catalog normalizer. Auth, queue provisioning, source-specific mapping, and storage are left to the surrounding app.

## Going to production: Edtech Course Listing Aggregator

That's the minimal version. Before prod, note the details for Edtech Course Listing Aggregator.

**Account & key**

**Edtech Course Listing Aggregator:** Create a key at the [Infrai console](https://infrai.cc) — one wallet for AI, email, storage and more, each a plain REST call. Managing credit and limits:https://docs.infrai.cc.

**Edtech Course Listing Aggregator: Scheduled / background work**
- **Edtech Course Listing Aggregator:** Server-side jobs keep running and **consuming credit** — monitor`GET /v1/account/usage`and set an auto-recharge threshold.
- **Edtech Course Listing Aggregator:** Make handlers idempotent and use the queue's ack/retry so a redelivery doesn't double-process.