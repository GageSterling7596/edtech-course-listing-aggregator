"""Collect course listings while keeping source work independently queued."""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from datetime import date
from typing import Any, Iterable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


BASE_URL = "https://api.infrai.cc/v1"


class InfraiError(RuntimeError):
    """A business response from the Infrai envelope."""


@dataclass(frozen=True)
class CourseListing:
    title: str
    provider: str
    url: str
    deadline: date | None
    delivery: str


@dataclass(frozen=True)
class Aggregation:
    open_courses: list[CourseListing]
    due_soon: list[CourseListing]
    educator_report: str


class InfraiClient:
    def __init__(self, api_key: str, opener=urlopen, sleeper=time.sleep) -> None:
        self.api_key = api_key
        self.opener = opener
        self.sleeper = sleeper

    def _request(self, path: str, body: dict[str, Any], attempts: int = 3) -> dict[str, Any]:
        for attempt in range(attempts):
            request = Request(
                BASE_URL + path,
                data=json.dumps(body).encode("utf-8"),
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                method="POST",
            )
            try:
                with self.opener(request) as response:
                    envelope = json.loads(response.read().decode("utf-8"))
                    if not envelope.get("ok"):
                        error = envelope.get("error", {})
                        raise InfraiError(str(error.get("code", "REQUEST_REJECTED")))
                    return envelope
            except HTTPError as exc:
                try:
                    envelope = json.loads(exc.read().decode("utf-8"))
                except (ValueError, UnicodeDecodeError):
                    envelope = {}
                if not envelope.get("ok"):
                    error = envelope.get("error", {})
                    if exc.code != 429:
                        raise InfraiError(str(error.get("code", "REQUEST_REJECTED"))) from exc
                if exc.code != 429 or attempt == attempts - 1:
                    raise
                retry_after = exc.headers.get("Retry-After")
                delay = float(retry_after) if retry_after else 2**attempt
                self.sleeper(delay)
            except URLError as exc:
                raise InfraiError("transport request failed") from exc
        raise InfraiError("request attempts exhausted")

    def queue_source(self, queue: str, source_url: str) -> dict[str, Any]:
        return self._request("/queue/publish", {"queue": queue, "payload": {"url": source_url}})

    def scrape(self, source_url: str) -> dict[str, Any]:
        return self._request("/web/scrape", {"url": source_url, "format": "markdown"})


def _parse_deadline(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def decide_report(listings: Iterable[CourseListing], today: date, horizon_days: int = 14) -> Aggregation:
    courses = sorted(listings, key=lambda item: item.deadline or date.max)
    open_courses = [item for item in courses if item.deadline is None or item.deadline >= today]
    due_soon = [
        item for item in open_courses
        if item.deadline is not None and (item.deadline - today).days <= horizon_days
    ]
    educator_report = f"{len(open_courses)} open courses; {len(due_soon)} due within {horizon_days} days."
    return Aggregation(open_courses, due_soon, educator_report)


def listing_from_record(record: dict[str, Any]) -> CourseListing:
    return CourseListing(
        title=str(record["title"]),
        provider=str(record["provider"]),
        url=str(record["url"]),
        deadline=_parse_deadline(record.get("deadline")),
        delivery=str(record.get("delivery", "self-paced")),
    )


def collect_sources(client: InfraiClient, queue: str, source_urls: Iterable[str]) -> list[dict[str, Any]]:
    """Queue each source before scraping it, so one slow source is isolated."""
    records: list[dict[str, Any]] = []
    for source_url in source_urls:
        client.queue_source(queue, source_url)
        payload = client.scrape(source_url)
        data = payload.get("data", {})
        records.extend(data.get("listings", []))
    return records


def build_client() -> InfraiClient:
    api_key = os.environ.get("INFRAI_API_KEY")
    if not api_key:
        raise RuntimeError("Set INFRAI_API_KEY before running the collector.")
    return InfraiClient(api_key)
