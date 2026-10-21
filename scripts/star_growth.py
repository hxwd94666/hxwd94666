"""Reconstruct retained-star growth from GitHub's public aggregate history."""
import datetime as dt


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
            'basis': 'public_aggregate_star_history', 'daily_by_repo': daily_by_repo,
            'total': sum(daily.values()),
            'received_30d': sum(n for day, n in daily.items() if str(start) <= day <= as_of),
            'points_30d': points}


def collect(repos, as_of, get):
    daily_by_repo = {}
    for repo in repos:
        if repo['fork']:
            continue
        daily = {}
        weeks = set()
        for page in range(1, 101):
            # Listing individual stargazers now requires collaborator access.
            # The aggregate history is public: never send a repository-scoped token.
            rows = get(f'https://api.github.com/repos/{repo["full_name"]}/stargazers/history?per_page=30&page={page}', authenticated=False)
            for row in rows:
                counts = row['days']
                assert type(row['week']) is int and row['week'] not in weeks, 'Invalid or repeated star-history week'
                assert len(counts) == 7 and all(type(n) is int and n >= 0 for n in counts), 'Incomplete star-history day counts'
                assert row['total'] == sum(counts), 'Star-history week total mismatch'
                weeks.add(row['week'])
                # The epoch labels the API's week. Do not re-bin daily aggregates
                # into Asia/Shanghai: GitHub does not promise UTC day boundaries.
                start = dt.datetime.fromtimestamp(row['week'], dt.timezone.utc).date()
                for i, count in enumerate(counts):
                    if count:
                        day = str(start + dt.timedelta(days=i))
                        assert day not in daily, 'Overlapping star-history weeks'
                        daily[day] = count
            if len(rows) < 30:
                break
        else:
            raise RuntimeError('Incomplete star-history pagination')
        assert sum(daily.values()) == repo['stargazers_count'], f'Star history/count mismatch for {repo["full_name"]}; retry with fresh counts'
        daily_by_repo[repo['name']] = daily
    return summarize(daily_by_repo, as_of)


def refresh(repos, as_of, get, previous=None):
    """Keep the last verified series when the public history request fails."""
    try:
        return collect(repos, as_of, get)
    except Exception as error:
        if previous:
            from refresh_state import error_reason
            return dict(previous, refresh_status='stale', refresh_error=error_reason(error))
        raise
