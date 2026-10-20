"""Exit 0 when data/stats.json already carries today's (Asia/Shanghai) date.

Used by update-stats.yml so the schedule can retry every six hours while still
producing at most one successful refresh per day.
"""
import datetime as dt
import json
import pathlib
import sys

today = dt.datetime.now(dt.timezone(dt.timedelta(hours=8))).date().isoformat()
stats = pathlib.Path(__file__).resolve().parents[1] / "data" / "stats.json"

stamp = ""
if stats.exists():
    try:
        data = json.loads(stats.read_text(encoding="utf-8"))
        stamp = str(data.get("as_of") or data.get("community_as_of") or "")
    except Exception:
        stamp = ""

fresh = stamp == today
print(f"today={today} as_of={stamp} fresh={fresh}")
sys.exit(0 if fresh else 1)
