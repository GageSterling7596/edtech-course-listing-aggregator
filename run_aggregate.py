import json
import os
from datetime import date

from src.edtech_aggregator import build_client, collect_sources, decide_report, listing_from_record


def main() -> None:
    urls = [item for item in os.environ.get("COURSE_SOURCE_URLS", "").split(",") if item]
    queue = os.environ.get("INFRAI_QUEUE", "edtech-course-sources")
    if not urls:
        raise SystemExit("Set COURSE_SOURCE_URLS to comma-separated listing URLs.")
    raw_records = collect_sources(build_client(), queue, urls)
    report = decide_report((listing_from_record(item) for item in raw_records), date.today())
    print(json.dumps({
        "open_courses": [item.__dict__ for item in report.open_courses],
        "due_soon": [item.__dict__ for item in report.due_soon],
        "educator_report": report.educator_report,
    }, default=str, indent=2))


if __name__ == "__main__":
    main()
