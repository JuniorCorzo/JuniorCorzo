#!/usr/bin/env python3
"""
Generate an animated GitHub-streak SVG (squares light up one by one).
Hardened against third-party data leaks (no external scraper fallback).
Consumes data/contributions.json produced by fetch_contributions.py.

Usage: python generate_streak_svg.py [username] [output.svg]
"""
import datetime
import json
import os
import sys
from typing import Any, Dict, List, Optional

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_DATA_PATH = os.path.join(HERE, "..", "data", "contributions.json")
DEFAULT_OUT_PATH = os.path.join(HERE, "..", "contrib-heatmap.svg")


def get_streak_data(user: str = "JuniorCorzo", data_file: Optional[str] = None) -> Dict[str, Any]:
    """Retrieve contribution streak data strictly from local verified snapshot or safe fallback."""
    snap = data_file or DEFAULT_DATA_PATH
    if os.path.exists(snap):
        try:
            with open(snap, "r", encoding="utf-8") as f:
                d = json.load(f)
            if all("level" in x for x in d.get("days", [])):
                return {
                    "contributions": d.get("days", []),
                    "total": {"lastYear": d.get("total_contributions", 0)},
                }
        except Exception:
            pass

    # Check local fallback snapshot if available
    local_snap = os.path.join(HERE, "contrib.json")
    if os.path.exists(local_snap):
        try:
            with open(local_snap, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass

    # Clean fallback data without external network calls
    return {"contributions": [], "total": {"lastYear": 0}}


def render_streak_svg(data: Dict[str, Any], user: str = "JuniorCorzo") -> str:
    """Render the animated streak SVG."""
    contribs: List[Dict[str, Any]] = data.get("contributions", [])
    total_dict = data.get("total", {})
    total: int = total_dict.get("lastYear", 0) if isinstance(total_dict, dict) else 0

    CELL, GAP, RAD, LEFT, TOP = 13, 3, 2.5, 34, 24
    COLORS = ["#161b22", "#0e4429", "#006d32", "#26a641", "#39d353"]
    GRAY = "#7d8590"
    MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

    n = len(contribs)
    NW = (n + 6) // 7 if n else 52
    W = LEFT + NW * (CELL + GAP) + 6
    H = TOP + 7 * (CELL + GAP) + 22

    REVEAL, DUR = 3.6, 0.55
    maxorder = (NW - 1) + 6 * 0.55 if NW > 1 else 1.0

    rects, labels = [], []
    if contribs:
        try:
            sd = datetime.date.fromisoformat(contribs[0]["date"])
        except Exception:
            sd = datetime.date.today()
    else:
        sd = datetime.date.today() - datetime.timedelta(days=364)

    last_m = None
    for wk in range(NW):
        d = sd + datetime.timedelta(days=wk * 7)
        if d.month != last_m:
            last_m = d.month
            labels.append(f'<text class="lbl" x="{LEFT+wk*(CELL+GAP)}" y="{TOP-8}">{MONTHS[d.month-1]}</text>')

    for name, r in [("Mon", 1), ("Wed", 3), ("Fri", 5)]:
        labels.append(f'<text class="lbl" x="2" y="{TOP+r*(CELL+GAP)+CELL-2}">{name}</text>')

    for i, c in enumerate(contribs):
        wk, row, lvl = i // 7, i % 7, c.get("level", 0)
        x = LEFT + wk * (CELL + GAP)
        y = TOP + row * (CELL + GAP)
        delay = round((wk + row * 0.55) / maxorder * REVEAL, 3) if maxorder else 0
        cls = "c g" if lvl >= 1 else "c e"
        fill_color = COLORS[min(lvl, len(COLORS) - 1)]
        rects.append(
            f'<rect class="{cls}" x="{x}" y="{y}" width="{CELL}" height="{CELL}" rx="{RAD}" '
            f'fill="{fill_color}" style="animation-delay:{delay}s"/>'
        )

    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" font-family="-apple-system,Segoe UI,Helvetica,Arial,sans-serif">
<style>
  text.lbl {{ fill:{GRAY}; font-size:13px; font-weight:600; }}
  text.total {{ fill:#e6edf3; font-size:15px; font-weight:700; }}
  .c {{ transform-box:fill-box; transform-origin:center; opacity:0; animation:pop {DUR}s ease-out both; }}
  .g {{ animation:pop {DUR}s ease-out both, flash {DUR+0.15}s ease-out both; }}
  @keyframes pop {{ 0%{{opacity:0;transform:scale(.2)}} 60%{{opacity:1;transform:scale(1.1)}} 100%{{opacity:1;transform:scale(1)}} }}
  @keyframes flash {{ 0%{{filter:brightness(2.4)}} 45%{{filter:brightness(2.4)}} 100%{{filter:brightness(1)}} }}
  @media (prefers-reduced-motion: reduce) {{ .c {{ opacity:1 !important; animation:none !important; }} }}
</style>
<rect width="{W}" height="{H}" fill="none"/>
{''.join(labels)}
{''.join(rects)}
<text class="total" x="{LEFT}" y="{H-6}">{total:,} contributions in the last year</text>
</svg>"""
    return svg


if __name__ == "__main__":
    user_arg = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("GH_PROFILE_USER", "JuniorCorzo")
    out_arg = sys.argv[2] if len(sys.argv) > 2 else DEFAULT_OUT_PATH

    streak_data = get_streak_data(user=user_arg)
    svg_output = render_streak_svg(streak_data, user=user_arg)

    os.makedirs(os.path.dirname(os.path.abspath(out_arg)), exist_ok=True)
    with open(out_arg, "w", encoding="utf-8") as f:
        f.write(svg_output)
    print(f"Wrote {out_arg}: {len(streak_data.get('contributions', []))} days, {len(svg_output)//1024} KB")
