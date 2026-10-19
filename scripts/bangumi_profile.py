"""Public anime collection counts, Bangumi v0 API."""
import datetime as dt,json
from urllib.request import Request,urlopen
USER='hxwd94666'
def collect():
    counts={}
    for kind in range(1,6):
        url=f'https://api.bgm.tv/v0/users/{USER}/collections?subject_type=2&type={kind}&limit=1'
        request=Request(url,headers={'User-Agent':'WuDu-Profile/1.0 (https://github.com/hxwd94666)'})
        with urlopen(request,timeout=30) as r:data=json.load(r)
        assert isinstance(data['total'],int) and data['total']>=0
        counts[str(kind)]=data['total']
    return {'username':USER,'url':f'https://bgm.tv/user/{USER}','as_of':str(dt.datetime.now(dt.timezone(dt.timedelta(hours=8))).date()),'subject_type':2,'counts':counts,'total':sum(counts.values())}
