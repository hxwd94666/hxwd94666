"""Anonymous public Bilibili metrics only. No cookies, account login or tokens."""
import datetime as dt
import copy
import json
from urllib.request import Request, urlopen

UID='436632831'


def request_json(url):
    request=Request(url,headers={'User-Agent':'Mozilla/5.0','Referer':'https://www.bilibili.com/','Accept':'application/json'})
    with urlopen(request,timeout=30) as response:
        return json.load(response)


def parse(card_response,relation_response,as_of):
    assert card_response.get('code')==0 and relation_response.get('code')==0,'Bilibili rejected anonymous request'
    info=card_response['data'];card=info['card'];relation=relation_response['data']
    assert str(card['mid'])==UID and str(relation['mid'])==UID,'Bilibili UID mismatch'
    metrics={'followers':relation['follower'],'following':relation['following'],
             'videos':info['archive_count'],'likes':info['like_num'],'level':card['level_info']['current_level']}
    assert all(type(value) is int and value>=0 for value in metrics.values()),'Incomplete public Bilibili metrics'
    assert info['follower']==metrics['followers'],'Follower count changed between requests; retry'
    return {'uid':UID,'url':f'https://space.bilibili.com/{UID}','name':card['name'],
            'avatar_url':card['face'],'as_of':as_of,'source':'anonymous_public_api',**metrics}


def collect():
    card=request_json(f'https://api.bilibili.com/x/web-interface/card?mid={UID}')
    relation=request_json(f'https://api.bilibili.com/x/relation/stat?vmid={UID}')
    today=str(dt.datetime.now(dt.timezone(dt.timedelta(hours=8))).date())
    return parse(card,relation,today)


def refresh(previous,fetch=None):
    try:return (fetch or collect)()
    except Exception as error:
        if not previous:raise
        preserved=copy.deepcopy(previous)
        from refresh_state import error_reason
        preserved['refresh_status']='stale'
        preserved['refresh_error']=error_reason(error)
        return preserved
