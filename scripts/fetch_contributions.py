#!/usr/bin/env python3
"""
Scrape real daily contribution counts from GitHub's public, unauthenticated
contributions endpoint and write data/contributions.json with raw days and
derived stats (current streak, longest streak, best day, monthly totals).

Hardened with regex username validation, UTF-8 encoding, and safe empty-data handling.
"""
import datetime
import json
import os
import re
import sys
from typing import Any, Dict, List, Optional, Tuple

import requests
from bs4 import BeautifulSoup

HERE = os.path.dirname(os.path.abspath(__file__))
OUT_PATH = os.path.join(HERE, "..", "data", "contributions.json")

# GitHub username policy: Alphanumeric and single hyphens, 1-39 characters, cannot begin or end with a hyphen
USERNAME_REGEX = re.compile(r"^[a-zA-Z0-9](?:[a-zA-Z0-9]|-(?=[a-zA-Z0-9])){0,38}$")


def validate_username(username: str) -> str:
    """Validate username against strict GitHub username regex."""
    if not isinstance(username, str) or not USERNAME_REGEX.match(username):
        raise ValueError(f"Invalid GitHub username: '{username}'")
    return username


def get_target_user(args: Optional[List[str]] = None) -> str:
    """Resolve target username from CLI args, environment variable, or default."""
    if args is None:
        args = sys.argv
    if len(args) > 1 and args[1]:
        candidate = args[1]
    else:
        candidate = os.environ.get("GH_PROFILE_USER", "JuniorCorzo")
    return validate_username(candidate)


def fetch_days(username: Optional[str] = None) -> List[Dict[str, Any]]:
    """Fetch contribution days from GitHub public contributions endpoint."""
    user = validate_username(username or get_target_user())
    url = f"https://github.com/users/{user}/contributions"
    headers = {"User-Agent": "profile-readme-bot/1.0"}

    resp = requests.get(url, headers=headers, timeout=30)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    cells = soup.select("td.ContributionCalendar-day")
    if not cells:
        return []

    days = []
    for td in cells:
        date = td.get("data-date")
        if not date:
            continue
        td_id = td.get("id")
        tooltip_el = soup.find("tool-tip", attrs={"for": td_id}) if td_id else None
        text = tooltip_el.get_text(strip=True) if tooltip_el else ""
        if re.search(r"no contributions", text, re.I):
            count = 0
        else:
            m = re.match(r"(\d+)", text)
            count = int(m.group(1)) if m else 0
        days.append({"date": date, "count": count, "level": int(td.get("data-level") or 0)})

    days.sort(key=lambda d: d["date"])
    return days


def compute_current_streak(days: List[Dict[str, Any]]) -> Tuple[int, Optional[str], Optional[str]]:
    """Calculate the current active contribution streak."""
    if not days:
        return 0, None, None

    idx = len(days) - 1
    if days[idx]["count"] == 0:
        idx -= 1  # today isn't over yet

    streak = 0
    end_idx = idx
    while idx >= 0 and days[idx]["count"] > 0:
        streak += 1
        idx -= 1
    start_idx = idx + 1
    if streak == 0:
        return 0, None, None
    return streak, days[start_idx]["date"], days[end_idx]["date"]


def compute_longest_streak(days: List[Dict[str, Any]]) -> Tuple[int, Optional[str], Optional[str]]:
    """Calculate the longest contribution streak."""
    if not days:
        return 0, None, None

    longest = run = 0
    longest_start = longest_end = None
    run_start_idx = None
    for i, d in enumerate(days):
        if d["count"] > 0:
            if run == 0:
                run_start_idx = i
            run += 1
            if run > longest:
                longest = run
                longest_start = days[run_start_idx]["date"]
                longest_end = days[i]["date"]
        else:
            run = 0
    return longest, longest_start, longest_end


def build_data(days: List[Dict[str, Any]], username: Optional[str] = None) -> Dict[str, Any]:
    """Compile raw calendar days into aggregated statistical payload."""
    user = username or get_target_user()
    total = sum(d["count"] for d in days) if days else 0
    active_days = sum(1 for d in days if d["count"] > 0) if days else 0
    best = max(days, key=lambda d: d["count"]) if days else {"date": None, "count": 0}
    cur_len, cur_start, cur_end = compute_current_streak(days)
    long_len, long_start, long_end = compute_longest_streak(days)

    monthly: Dict[str, int] = {}
    for d in days:
        key = d["date"][:7]
        monthly[key] = monthly.get(key, 0) + d["count"]
    monthly_list = [{"month": k, "total": v} for k, v in sorted(monthly.items())]

    range_data = {"start": days[0]["date"], "end": days[-1]["date"]} if days else {"start": None, "end": None}

    return {
        "username": user,
        "generated_at": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "range": range_data,
        "total_contributions": total,
        "active_days": active_days,
        "avg_per_active_day": round(total / active_days, 1) if active_days else 0,
        "current_streak": {"length": cur_len, "start": cur_start, "end": cur_end},
        "longest_streak": {"length": long_len, "start": long_start, "end": long_end},
        "best_day": {"date": best["date"], "count": best["count"]},
        "monthly": monthly_list,
        "days": days,
    }


def save_contributions(data: Dict[str, Any], output_path: Optional[str] = None) -> None:
    """Save contributions data dictionary to JSON file using UTF-8."""
    target_path = output_path or OUT_PATH
    os.makedirs(os.path.dirname(os.path.abspath(target_path)), exist_ok=True)
    with open(target_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


if __name__ == "__main__":
    target_user = get_target_user()
    print(f"Fetching contributions for {target_user}...")
    fetched_days = fetch_days(target_user)
    payload = build_data(fetched_days, username=target_user)
    save_contributions(payload)
    print(
        f"Wrote {OUT_PATH}: {payload['total_contributions']} contributions, "
        f"current streak {payload['current_streak']['length']}, "
        f"longest streak {payload['longest_streak']['length']}"
    )
