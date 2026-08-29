#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
from datetime import date, timedelta
from pathlib import Path

PALETTE = [
    "#161b22",
    "#0e4429",
    "#006d32",
    "#26a641",
    "#39d353",
    "#69f0a0",
]


def load_contributions(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def clamp(value: int, low: int, high: int) -> int:
    return max(low, min(high, value))


def level_for_count(count: int, max_count: int) -> int:
    if count <= 0:
        return 0
    if max_count <= 0:
        return 1
    ratio = count / max_count
    if ratio <= 0.09:
        return 1
    if ratio <= 0.25:
        return 2
    if ratio <= 0.45:
        return 3
    if ratio <= 0.7:
        return 4
    return 5


def color_for_count(count: int, max_count: int) -> str:
    return PALETTE[level_for_count(count, max_count)]


def build_calendar_grid(days: list[dict]) -> tuple[list[dict], int, int]:
    if not days:
        return [], 0, 0

    ordered = sorted(days, key=lambda item: item["date"])
    start_date = date.fromisoformat(ordered[0]["date"])
    end_date = date.fromisoformat(ordered[-1]["date"])
    start_offset = (start_date.weekday() + 1) % 7
    end_offset = (6 - end_date.weekday()) % 7
    grid_start = start_date - timedelta(days=start_offset)
    grid_end = end_date + timedelta(days=end_offset)

    total_days = (grid_end - grid_start).days + 1
    total_weeks = (total_days + 6) // 7
    max_count = max((int(day.get("count", 0)) for day in ordered), default=0)

    cells: list[dict] = []
    count_by_date = {day["date"]: int(day.get("count", 0)) for day in ordered}

    for offset in range(total_days):
        current = grid_start + timedelta(days=offset)
        current_key = current.isoformat()
        count = count_by_date.get(current_key, 0)
        week_index = offset // 7
        day_index = offset % 7
        cells.append(
            {
                "date": current_key,
                "count": count,
                "week": week_index,
                "day": day_index,
                "color": color_for_count(count, max_count),
            }
        )

    return cells, total_weeks, max_count


def render_svg(cells: list[dict], total_weeks: int, total_contributions: int) -> str:
    cell_size = 11
    gap = 3
    margin_left = 35
    margin_top = 30
    width = margin_left + (total_weeks * (cell_size + gap)) + 10
    height = margin_top + (7 * (cell_size + gap)) + 80

    rows = []
    for cell in cells:
        x = margin_left + (cell["week"] * (cell_size + gap))
        y = margin_top + (cell["day"] * (cell_size + gap))
        dx = cell["week"] * 2.2
        dy = cell["day"] * 2.2
        rows.append(
            f'<rect class="cell" x="{x}" y="{y}" width="{cell_size}" height="{cell_size}" rx="2.5" fill="{cell["color"]}" style="--dx:{dx}px; --dy:{dy}px; animation-delay:{(cell["week"] * 0.028 + cell["day"] * 0.022):.3f}s;" />'
        )

    legend_items = []
    for idx, color in enumerate(PALETTE):
        x = margin_left + idx * 16
        legend_items.append(
            f'<rect x="{x}" y="{height - 34}" width="11" height="11" rx="2" fill="{color}" />'
        )

    legend_start = margin_left + 6 * 16 + 14
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-label="GitHub contribution heatmap">
  <style>
    .cell {{
      opacity: 0;
      transform: translate(var(--dx), var(--dy));
      animation: reveal 0.55s ease-in-out forwards;
      transform-box: fill-box;
      transform-origin: center;
    }}
    @keyframes reveal {{
      0% {{
        opacity: 0;
        transform: translate(-12px, -12px) scale(0.9);
      }}
      100% {{
        opacity: 1;
        transform: translate(0, 0) scale(1);
      }}
    }}
    .label {{
      font: 12px -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
      fill: #c9d1d9;
    }}
    .meta {{
      font: 12px -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
      fill: #8b949e;
    }}
  </style>
  <rect width="100%" height="100%" fill="#0d1117"/>
  <text x="{margin_left}" y="18" class="meta">GitHub contribution calendar</text>
  {''.join(rows)}
  <text x="{margin_left}" y="{height - 14}" class="label">Less</text>
  {''.join(legend_items)}
  <text x="{legend_start}" y="{height - 14}" class="label">→</text>
  <text x="{legend_start + 14}" y="{height - 14}" class="label">More</text>
  <text x="{margin_left}" y="{height - 52}" class="label" font-size="15" font-weight="600">{total_contributions:,} contributions in the last year</text>
</svg>
'''
    return svg


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Render a GitHub contribution heatmap from JSON data.")
    parser.add_argument("--input", type=Path, default=Path("data/contributions.json"), help="JSON file produced by fetch_contributions.py.")
    parser.add_argument("--output", type=Path, default=Path("contrib-heatmap.svg"), help="SVG file to write.")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    data = load_contributions(args.input)
    days = data.get("days", [])
    cells, total_weeks, _ = build_calendar_grid(days)
    total_contributions = int(data.get("stats", {}).get("total", sum(int(day.get("count", 0)) for day in days)))
    svg = render_svg(cells, total_weeks, total_contributions)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(svg, encoding="utf-8")
