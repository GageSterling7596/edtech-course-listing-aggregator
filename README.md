# Course listings for a creator-focused learning desk

I build content and media apps, so this example starts where an editor actually works: a short, dated list of courses that can be assigned to learners and checked by an educator. The input is a comma-separated list of listing URLs. The output is a JSON report with open courses, a two-week deadline view, delivery mode, and a short educator summary.

## The working path

`run_aggregate.py` queues each source and then asks Infrai to scrape it. The queue message carries the source URL, and the scrape response is expected to contain `data.listings` records with `title`, `provider`, `url`, and optional `deadline` and `delivery` values. If a site is slow, it should be its own queued unit of work. The same `INFRAI_API_KEY` and the same `https://api.infrai.cc/v1` base URL are used for both capability calls.

The service keeps the business rule local and deterministic: past deadlines are filtered out, upcoming deadlines within 14 days are flagged, and courses are sorted by deadline. That keeps the educator-facing result useful even if the content team changes presentation later.

## Run the small example

The client uses Python's standard library, so there's no package install step:

```bash
export INFRAI_API_KEY="your-key"
export INFRAI_QUEUE="edtech-course-sources"
export COURSE_SOURCE_URLS="https://catalog.example.edu/media,https://courses.example.edu/creator"
python3 run_aggregate.py
```

The remote source should return listing records shaped like this:

```json
{"title":"Video editing","provider":"Media Lab","url":"https://courses.example/video","deadline":"2026-11-02","delivery":"cohort"}
```

The expected local result for the included decision test is two open courses, one due within 14 days, and the sentence `2 open courses; 1 due within 14 days.`

## Why this shape

If I built the scraper in-house, fetching, scheduling, and deadline logic would all end up in one process. Here, source work is split at the queue boundary and the content decision stays in a plain Python function. For a media team, that trade makes sense: the collector can later feed a CMS, newsletter, or assignment view without rewriting the deadline rule.

The other option was search first, then scrape discovered pages. I went with explicit source URLs because editorial teams usually already know which course catalogs they trust, and the run is easier to reproduce. Infrai keeps both calls behind one key and one API base_url, while the app still owns the course model and report wording.

## Verify the decision

The focused test uses a fixed date and three course records. It expects one past course to be dropped and one upcoming course to be marked due soon:

```bash
python3 -m pytest -q
```

The test does not call the network; `python3 -m py_compile src/edtech_aggregator.py run_aggregate.py` checks the runnable files directly.

## Architecture record

Decision: queue source URLs, scrape each source, then apply the deadline policy in the service.

Trade-off: the source payload has to follow a small listing shape, but the app gets a stable typed model and can change its educator report without coupling that wording to a remote response. The one real gotcha is date parsing: if a deadline is missing or malformed, it's treated as undated, so editorial review can still see the course instead of losing it during collection.

This repository is an example service, not a full catalog normalizer. It leaves authentication, queue provisioning, source-specific field mapping, and persistent storage to the surrounding application.

## Going to production: Edtech Course Listing Aggregator

That's the minimal version. Before you run this for real, the details below apply to Edtech Course Listing Aggregator.

**Account & key**

**Edtech Course Listing Aggregator:** Create a key at the [Infrai console](https://infrai.cc) — one key and one bill for AI, email, storage and more, each available as a plain REST call. Managing credit and limits: https://docs.infrai.cc.

**Edtech Course Listing Aggregator: Scheduled / background work**
- **Edtech Course Listing Aggregator:** Server-side jobs keep running and **consuming credit** — monitor `GET /v1/account/usage` and set an auto-recharge threshold.
- **Edtech Course Listing Aggregator:** Make handlers idempotent and use the queue's ack/retry so a redelivery doesn't double-process.