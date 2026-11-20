"""Star growth from daily snapshots of each repository's star count.

GitHub publishes no per-day star history through a documented API, and the
undocumented aggregate endpoint that used to back this card is no longer
called. Every refresh records today's total for each owned repository; daily
increments are derived from consecutive snapshots, so the series keeps growing
from the day this module was switched over.
"""
import datetime as dt
import json
from pathlib import Path

STATE = Path(__file__).resolve().parents[1] / 'data/star_history.json'


def summarize(daily_by_repo, as_of):
    end = dt.date.fromisoformat(as_of)
    start = end - dt.timedelta(days=29)
    daily = {}
    for counts in daily_by_repo.values():
        for day, count in counts.items():
            assert dt.date.fromisoformat(day) <= end, 'Star history exceeds snapshot date'
            daily[day] = daily.get(day, 0) + count
    points = []
    for i in range(30):
        day = str(start + dt.timedelta(days=i))
        points.append({'date': day, 'count': sum(n for date, n in daily.items() if date <= day)})
    return {'as_of': as_of, 'timezone': 'GitHub-defined day buckets',
            'basis': 'daily_star_count_snapshots', 'daily_by_repo': daily_by_repo,
            'total': sum(daily.values()),
            'received_30d': sum(n for day, n in daily.items() if str(start) <= day <= as_of),
            'points_30d': points}


def load(path=STATE):
    try:
        return json.loads(Path(path).read_text(encoding='utf-8'))
    except FileNotFoundError:
        return {}


def save(series, path=STATE):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(series, indent=2, sort_keys=True) + '\n', encoding='utf-8', newline='\n')


def to_increments(series):
    """Turn cumulative per-day totals into the per-day star gains the cards draw."""
    gains = {}
    for name, points in series.items():
        daily = {}
        previous = None
        for day in sorted(points):
            value = points[day]
            if previous is not None and value > previous:
                daily[day] = value - previous
            previous = value
        gains[name] = daily
    return gains


def collect(repos, as_of, get=None, path=STATE):
    """Record today's star totals, then summarise the last 30 days of gains."""
    series = {name: {day: value for day, value in points.items() if day <= as_of}
              for name, points in load(path).items()}
    for repo in repos:
        if repo['fork']:
            continue
        points = series.setdefault(repo['name'], {})
        points[as_of] = int(repo['stargazers_count'])
    save(series, path)
    return summarize(to_increments(series), as_of)


def refresh(repos, as_of, get, previous=None, path=STATE):
    """Keep the last verified series when today's snapshot cannot be written."""
    try:
        return collect(repos, as_of, get, path=path)
    except Exception as error:
        if previous:
            from refresh_state import error_reason
            return dict(previous, refresh_status='stale', refresh_error=error_reason(error))
        raise
