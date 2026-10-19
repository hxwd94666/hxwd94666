"""Read only public Steam Community profile fields. No login or API key."""
import datetime as dt,html,re,xml.etree.ElementTree as ET
from urllib.request import Request,urlopen

STEAM_ID='76561198402274250'
URL=f'https://steamcommunity.com/profiles/{STEAM_ID}/'

def parse(xml_text,page,as_of):
    root=ET.fromstring(xml_text)
    assert root.tag=='profile' and root.findtext('steamID64')==STEAM_ID
    result={'id':STEAM_ID,'url':URL,'name':root.findtext('steamID'),'state':root.findtext('onlineState'),'member_since':root.findtext('memberSince'),'privacy':root.findtext('privacyState'),'as_of':as_of}
    level=re.search(r'class="friendPlayerLevelNum">([0-9]+)</span>',page)
    if level:result['level']=int(level[1])
    for label,key in [('Games','games'),('Badges','badges')]:
        match=re.search(r'count_link_label">\s*'+label+r'</span>.*?profile_count_link_total">\s*([\d,]+)',page,re.S)
        if match:result[key]=int(match[1].replace(',',''))
    return result

def collect():
    def read(url):
        with urlopen(Request(url,headers={'User-Agent':'WuDu-GitHub-Profile','Accept-Language':'en-US,en;q=0.9'}),timeout=35) as r:return r.read().decode('utf-8')
    return parse(read(URL+'?xml=1'),read(URL),str(dt.datetime.now(dt.timezone(dt.timedelta(hours=8))).date()))
