"""Current retained stargazers by timestamp; not historical net star totals."""
import datetime as dt


def summarize(dates_by_repo, as_of):
    end = dt.date.fromisoformat(as_of)
    start = end - dt.timedelta(days=29)
    dates = [dt.datetime.fromisoformat(value.replace('Z', '+00:00')).astimezone(dt.timezone(dt.timedelta(hours=8))).date()
             for values in dates_by_repo.values() for value in values]
    assert all(day <= end for day in dates), 'Star timestamps exceed snapshot date'
    points = []
    for i in range(30):
        day = start + dt.timedelta(days=i)
        points.append({'date': str(day), 'count': sum(value <= day for value in dates)})
    return {'as_of': as_of, 'timezone': 'Asia/Shanghai', 'basis': 'currently_retained_stargazers',
            'dates_by_repo': dates_by_repo, 'total': len(dates),
            'received_30d': sum(start <= day <= end for day in dates), 'points_30d': points}


def collect(repos, as_of, get):
    dates = {}
    for repo in repos:
        if repo['fork']:
            continue
        values = []
        for page in range(1, 1001):
            data = get(f'https://api.github.com/repos/{repo["full_name"]}/stargazers?per_page=100&page={page}', accept='application/vnd.github.star+json')
            values.extend(row['starred_at'] for row in data)
            if len(data) < 100:
                break
        else:
            raise RuntimeError('Incomplete stargazers pagination')
        assert len(values) == repo['stargazers_count'], 'Star count changed during collection; rerun'
        dates[repo['name']] = values
    return summarize(dates, as_of)


def refresh(repos, as_of, get, previous=None):
    """Keep the last verified series when GitHub temporarily rejects the API request."""
    try:
        return collect(repos, as_of, get)
    except Exception:
        if previous:
            return dict(previous, refresh_status='stale')
        raise
