#!/usr/bin/env python3
"""Synchronise public ORCID works into the static website publication feed."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

ORCID_ID = "0000-0003-2683-0515"
ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "data" / "orcid-works.json"
HEADERS = {
    "Accept": "application/vnd.orcid+json, application/json",
    "User-Agent": "Bolong-Liu-Academic-Homepage/1.0 (https://yuzhongbaima.github.io/bolong-liu/)",
}


def fetch_json(url: str) -> dict[str, Any]:
    request = Request(url, headers=HEADERS)
    with urlopen(request, timeout=30) as response:
        return json.load(response)


def nested_value(record: dict[str, Any], *keys: str) -> str | None:
    value: Any = record
    for key in keys:
        if not isinstance(value, dict):
            return None
        value = value.get(key)
    return value if isinstance(value, str) and value else None


def initials(given_name: str) -> str:
    return "".join(part[0].upper() for part in given_name.replace("-", " ").split() if part)


def format_authors(authors: list[dict[str, Any]]) -> list[str]:
    formatted = []
    for author in authors:
        family = author.get("family", "").strip()
        given = author.get("given", "").strip()
        if family and given:
            formatted.append(f"{family} {initials(given)}")
        elif family:
            formatted.append(family)
    return ["Pan D" if author == "Pa D" else author for author in formatted]


def orcid_authors(put_code: int | None) -> list[str]:
    if not put_code:
        return []
    try:
        work = fetch_json(f"https://pub.orcid.org/v3.0/{ORCID_ID}/work/{put_code}")
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError):
        return []

    authors = []
    for contributor in (work.get("contributors") or {}).get("contributor", []):
        credit_name = nested_value(contributor, "credit-name", "value")
        if not credit_name:
            continue
        family, separator, given = credit_name.partition(",")
        authors.append(f"{family.strip()} {given.strip().replace('.', '')}" if separator else credit_name)
    return authors


def find_doi(external_ids: dict[str, Any] | None) -> str | None:
    for external_id in (external_ids or {}).get("external-id", []):
        if external_id.get("external-id-type") == "doi":
            value = external_id.get("external-id-value", "").strip().lower()
            return value or None
    return None


def publication_date(summary: dict[str, Any]) -> tuple[str, int]:
    date = summary.get("publication-date") or {}
    year = nested_value(date, "year", "value") or "0000"
    month = nested_value(date, "month", "value") or "00"
    return year, int(month) if month.isdigit() else 0


def crossref_metadata(doi: str) -> dict[str, Any]:
    try:
        return fetch_json(f"https://api.crossref.org/works/{quote(doi, safe='')}").get("message", {})
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError):
        return {}


def build_work(group: dict[str, Any]) -> dict[str, Any] | None:
    summaries = group.get("work-summary", [])
    if not summaries:
        return None
    summary = summaries[0]
    title = nested_value(summary, "title", "title", "value")
    if not title:
        return None

    doi = find_doi(group.get("external-ids")) or find_doi(summary.get("external-ids"))
    metadata = crossref_metadata(doi) if doi else {}
    year, month = publication_date(summary)
    crossref_title = (metadata.get("title") or [None])[0]
    journal = (metadata.get("container-title") or [None])[0] or nested_value(summary, "journal-title", "value")
    authors = format_authors(metadata.get("author", [])) or orcid_authors(summary.get("put-code")) or ["Bolong Liu"]

    return {
        "title": crossref_title or title,
        "authors": authors,
        "journal": journal,
        "year": year,
        "month": month,
        "volume": metadata.get("volume"),
        "issue": metadata.get("issue"),
        "page": metadata.get("page") or metadata.get("article-number"),
        "doi": doi,
        "type": summary.get("type", "other"),
    }


def work_key(work: dict[str, Any]) -> str:
    if work["doi"]:
        return f"doi:{work['doi'].lower()}"
    return f"title:{work['title'].casefold()}:{work['year']}"


def main() -> None:
    record = fetch_json(f"https://pub.orcid.org/v3.0/{ORCID_ID}/works")
    unique: dict[str, dict[str, Any]] = {}
    for group in record.get("group", []):
        work = build_work(group)
        if work:
            unique.setdefault(work_key(work), work)

    works = sorted(
        unique.values(),
        key=lambda work: (int(work["year"]) if work["year"].isdigit() else 0, work["month"], work["title"]),
        reverse=True,
    )
    payload = {"orcid": ORCID_ID, "works": works}

    if OUTPUT.exists():
        existing = json.loads(OUTPUT.read_text(encoding="utf-8"))
        if existing.get("orcid") == payload["orcid"] and existing.get("works") == payload["works"]:
            print("ORCID works are unchanged.")
            return

    payload["synchronised_at"] = datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(works)} unique ORCID works to {OUTPUT.relative_to(ROOT)}.")


if __name__ == "__main__":
    main()
