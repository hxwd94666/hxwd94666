"""Generate GitHub profile SVGs from public data. Python standard library only."""
import argparse, calendar, collections, datetime as dt, html, json, os, re
from pathlib import Path
from html.parser import HTMLParser
from urllib.request import Request, urlopen
from urllib.parse import quote

USER = 'hxwd94666'
PROJECT = 'NTE-Drive-Calculator'

def get(url, api=True, accept=None, authenticated=True):
    headers={'User-Agent':'WuDu-Profile','Accept':accept or ('application/vnd.github+json' if api else 'text/html')}
    if api and authenticated and os.environ.get('GH_TOKEN'):
        headers['Authorization']='Bearer '+os.environ['GH_TOKEN']
    with urlopen(Request(url,headers=headers),timeout=45) as r:
        content=r.read().decode('utf-8')
    return json.loads(content) if api else content

def pages(url):
    items=[]
    for page in range(1,1001):
        batch=get(url+('&' if '?' in url else '?')+f'per_page=100&page={page}')
        items.extend(batch)
        if len(batch)<100:return items
    raise RuntimeError('Pagination limit exceeded')

CONTRIBUTIONS_QUERY='''query($from:DateTime!,$to:DateTime!){
  viewer{contributionsCollection(from:$from,to:$to){
    contributionCalendar{weeks{contributionDays{date contributionCount}}}
  }}
}'''


def graphql(query,variables):
    token=os.environ.get('GH_TOKEN') or os.environ.get('GITHUB_TOKEN')
    if not token:raise RuntimeError('GH_TOKEN is required for GraphQL')
    body=json.dumps({'query':query,'variables':variables}).encode('utf-8')
    request=Request('https://api.github.com/graphql',data=body,method='POST',
                     headers={'Authorization':'Bearer '+token,'Content-Type':'application/json',
                              'Accept':'application/json','User-Agent':'WuDu-Profile'})
    with urlopen(request,timeout=45) as response:
        payload=json.loads(response.read().decode('utf-8'))
    if payload.get('errors'):
        raise RuntimeError('GraphQL: '+'; '.join(str(e.get('message','?')) for e in payload['errors']))
    return payload['data']


def collect_contributions(today):
    """Year-to-date contribution days from the documented GraphQL calendar."""
    data=graphql(CONTRIBUTIONS_QUERY,{'from':f'{today[:4]}-01-01T00:00:00Z','to':f'{today}T23:59:59Z'})
    weeks=data['viewer']['contributionsCollection']['contributionCalendar']['weeks']
    counts={day['date']:day['contributionCount'] for week in weeks for day in week['contributionDays']}
    end=dt.date.fromisoformat(today);cursor=dt.date.fromisoformat(f'{today[:4]}-01-01')
    days=[]
    while cursor<=end:
        key=cursor.isoformat()
        if key not in counts:raise ValueError('Missing contribution day '+key)
        days.append({'date':key,'count':counts[key]})
        cursor+=dt.timedelta(days=1)
    peak=max((d['count'] for d in days),default=0) or 1
    for d in days:
        d['level']=0 if d['count']==0 else 1+min(3,round(3*d['count']/peak))
    assert len(days)==end.timetuple().tm_yday,'Incomplete calendar'
    return days

def collect_repos():
    return [r for r in pages(f'https://api.github.com/users/{USER}/repos?type=owner') if not r['private']]


def collect_github(today, repos):
    releases=[r for r in pages(f'https://api.github.com/repos/{USER}/{PROJECT}/releases') if not r['draft']]
    days=collect_contributions(today)
    account_data=get(f'https://api.github.com/users/{USER}')
    account={k:account_data.get(k) for k in ['created_at','followers','following','public_repos','public_gists']}
    languages_by_repo={r['name']:get(r['languages_url']) for r in repos if not r['fork']}
    fields=['name','full_name','fork','stargazers_count','forks_count','language','html_url','open_issues_count']
    slim_repos=[dict({k:r.get(k) for k in fields},license_spdx=(r.get('license') or {}).get('spdx_id')) for r in repos]
    return {'account':account,'languages_by_repo':languages_by_repo,'as_of':today,'repos':slim_repos,
            'releases':[{'tag_name':r['tag_name'],'draft':False,'prerelease':r['prerelease'],'published_at':r['published_at'],
                         'assets':[{'name':a['name'],'download_count':a['download_count']} for a in r['assets']]} for r in releases], 'days':days}


def collect_community():
    queries={'issues_open':'type:issue is:open','issues_closed':'type:issue is:closed','prs_open':'type:pr is:open','prs_merged':'type:pr is:merged','prs_closed_unmerged':'type:pr is:closed is:unmerged'}
    community={}
    for name,q in queries.items():
        result=get('https://api.github.com/search/issues?q='+quote(f'author:{USER} '+q)+'&per_page=1')
        assert not result.get('incomplete_results'),'Incomplete community search'
        community[name]=result['total_count']
    return community


def collect(previous=None, force=False, today=None):
    from copy import deepcopy
    from refresh_state import MODULES, due_modules, error_reason, has_data, today_local
    from star_growth import collect as collect_star_growth
    from steam_profile import collect as collect_steam
    from bangumi_profile import collect as collect_bangumi
    from bilibili_profile import collect as collect_bilibili

    data=deepcopy(previous or {})
    today=today or today_local()
    due=due_modules(data,today,force)
    if not due:
        print('All modules are fresh; no requests made')
        return data
    # Reuse this run's live repository list, never validate new star history
    # against a count from yesterday (or an earlier scheduled run).
    repos=None
    def live_repos():
        nonlocal repos
        if repos is None:
            repos=collect_repos()
        return repos
    collectors={'github':lambda:collect_github(today,live_repos()),
                'community':collect_community,
                'star_growth':lambda:collect_star_growth(live_repos(),today,get),
                'steam':collect_steam,'bangumi':collect_bangumi,'bilibili':collect_bilibili}
    states=data.setdefault('refresh',{})
    for module in due:
        attempted=dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds')
        try:
            value=collectors[module]()
            if not value:
                raise ValueError('Collector returned no data')
            if module=='github':
                data.update(value)
            else:
                value.pop('refresh_status',None)
                value.pop('refresh_error',None)
                data[module]=value
                if module=='community':data['community_as_of']=today
            states[module]={'status':'fresh','attempted_at':attempted}
            print(f'{module}: refreshed')
        except Exception as error:
            reason=error_reason(error)
            states[module]={'status':'stale','attempted_at':attempted,'error':reason}
            print(f'{module}: stale; {reason}')
    missing=[module for module in MODULES if not has_data(data,module)]
    if missing:
        # A first-ever failed collection has no verified values to render.
        reasons='; '.join(f'{m}: {states.get(m,{}).get("error","missing data")}' for m in missing)
        raise RuntimeError('No baseline for required modules: '+reasons)
    data.setdefault('username',USER)
    data.setdefault('platform_links',{'afdian':'https://afdian.com/a/hxwd94666'})
    return data

from dense_cards import render

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--snapshot',type=Path);ap.add_argument('--force',action='store_true',help='Refresh all modules even when already fresh today');ap.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1]);args=ap.parse_args()
    previous=args.root/'data/stats.json'
    data=json.loads(args.snapshot.read_text(encoding='utf-8')) if args.snapshot else collect(json.loads(previous.read_text(encoding='utf-8')) if previous.is_file() else {},force=args.force)
    summary=render(data,args.root)
    (args.root/'data').mkdir(exist_ok=True)
    (args.root/'data/stats.json').write_text(json.dumps(data,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps(summary,sort_keys=True))
if __name__=='__main__':main()
