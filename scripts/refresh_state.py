"""Shared module freshness and public refresh diagnostics."""
import datetime as dt
import os
import re

MODULES = ('github', 'community', 'star_growth', 'steam', 'bangumi', 'bilibili')
GITHUB_FIELDS = ('account', 'languages_by_repo', 'repos', 'releases', 'days')


def today_local():
    return dt.datetime.now(dt.timezone(dt.timedelta(hours=8))).date().isoformat()


def has_data(data, module):
    if module == 'github':
        return all(data.get(key) is not None for key in GITHUB_FIELDS) and bool(data.get('days'))
    return bool(data.get(module))


def data_date(data, module):
    if module == 'github':
        return data.get('as_of', '')
    if module == 'community':
        return data.get('community_as_of', '')
    return (data.get(module) or {}).get('as_of', '')


def is_stale(data, module):
    state = data.get('refresh', {}).get(module, {})
    payload = data.get(module) or {}
    return state.get('status') == 'stale' or payload.get('refresh_status') == 'stale'


def due_modules(data, today, force=False):
    return [module for module in MODULES if force or not has_data(data, module)
            or data_date(data, module) != today or is_stale(data, module)]


def error_reason(error):
    # Diagnostics are published with the snapshot; never include bearer credentials.
    reason = f'{type(error).__name__}: {error}'
    for name in ('GH_TOKEN', 'GITHUB_TOKEN'):
        token = os.environ.get(name)
        if token:
            reason = reason.replace(token, '[REDACTED]')
    reason = re.sub(r'(?i)bearer\s+[^\s,;]+', 'Bearer [REDACTED]', reason)
    return ' '.join(reason.split())[:500]


def label(data, module):
    stamp = data_date(data, module) or 'UNKNOWN'
    return ('STALE / ' if is_stale(data, module) else 'AS OF ') + stamp


def description(data, module):
    state = data.get('refresh', {}).get(module, {})
    payload = data.get(module) or {}
    reason = state.get('error') or payload.get('refresh_error')
    return label(data, module) + (f' / {reason}' if reason else '')
