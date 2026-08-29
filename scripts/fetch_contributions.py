#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests
from bs4 import BeautifulSoup

DEFAULT_USERNAME = "rachitneema03"


def fetch_contribution_html(username: str) -> str:
    url = f"https://github.com/users/{username}/contributions"
    response = requests.get(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (compatible; GitHubContribBot/1.0)",
            "Accept-Language": "en-US,en;q=0.9",
        },
        timeout=30,
    )
    response.raise_for_status()
    return response.text


def parse_count_from_label(label: str) -> int:
    text = (label or "").strip().lower()
    if not text:
        return 0
    if "no contributions" in text:
        return 0
    match = re.search(r"(\d+)\s+contribution", text)
    if match:
        return int(match.group(1))
    match = re.search(r"(\d+)\s+contributions", text)
    if match:
        return int(match.group(1))
    return 0


def extract_day_rows(html_text: str) -> list[dict[str, Any]]:
    soup = BeautifulSoup(html_text, "html.parser")
    rows: list[dict[str, Any]] = []

    for cell in soup.select("td.ContributionCalendar-day"):
        date_value = (cell.get("data-date") or "").strip()
        if not date_value:
            continue

        level = int(cell.get("data-level") or 0)
        tooltip = cell.find_next_sibling("tool-tip")
        label = tooltip.get_text(" ", strip=True) if tooltip else ""
        count = parse_count_from_label(label)
        if count == 0 and level > 0:
            count = level

        rows.append(
            {
                "date": date_value,
                "count": count,
                "level": level,
            }
        )

    rows.sort(key=lambda item: item["date"])
    return rows


def build_month_totals(days: list[dict[str, Any]]) -> dict[str, int]:
    totals: defaultdict[str, int] = defaultdict(int)
    for day in days:
        month_key = day["date"][:7]
        totals[month_key] += int(day["count"])
    return dict(sorted(totals.items()))


def calculate_stats(days: list[dict[str, Any]]) -> dict[str, Any]:
    if not days:
        return {
            "current_streak": 0,
            "longest_streak": 0,
            "best_day": {"date": None, "count": 0},
            "monthly_totals": {},
            "total": 0,
        }

    ordered = sorted(days, key=lambda item: item["date"])
    total = sum(int(item["count"]) for item in ordered)

    current_streak = 0
    for day in reversed(ordered):
        if day["count"] > 0:
            current_streak += 1
        else:
            break

    longest_streak = 0
    running = 0
    for day in ordered:
        if day["count"] > 0:
            running += 1
            longest_streak = max(longest_streak, running)
        else:
            running = 0

    best_day = max(ordered, key=lambda item: item["count"])

    return {
        "current_streak": current_streak,
        "longest_streak": longest_streak,
        "best_day": {"date": best_day["date"], "count": int(best_day["count"])},
        "monthly_totals": build_month_totals(ordered),
        "total": total,
    }


def write_contributions(username: str, output_path: Path) -> dict[str, Any]:
    html = fetch_contribution_html(username)
    days = extract_day_rows(html)
    record = {
        "username": username,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "days": days,
        "stats": calculate_stats(days),
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(record, indent=2), encoding="utf-8")
    return record


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fetch a GitHub contribution calendar without a token.")
    parser.add_argument("--username", default=DEFAULT_USERNAME, help="GitHub username to scrape.")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/contributions.json"),
        help="Path for the JSON output file.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    write_contributions(args.username, args.output)
