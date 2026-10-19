"""Dense public-data cards. All numbers derive from the existing snapshot."""
import calendar, collections, datetime as dt, html

def render(data,root):
    out=root/'assets'/'cards';out.mkdir(exist_ok=True,parents=True)
    repos=data['repos'];owned=[r for r in repos if not r['fork']]
    releases=[r for r in data['releases'] if not r.get('draft')]
    days=data['days'];asof=dt.date.fromisoformat(data['as_of']);year=asof.year
    total=sum(d['count'] for d in days);active=sum(d['count']>0 for d in days)
    longest=run=0
    for d in days:
        run=run+1 if d['count'] else 0;longest=max(longest,run)
    current=0
    for d in reversed(days if days[-1]['count'] else days[:-1]):
        if not d['count']:break
        current+=1
    downloads=sum(a['download_count'] for r in releases for a in r['assets'])
    stars=sum(r['stargazers_count'] for r in owned);forks=sum(r['forks_count'] for r in owned)
    months=[sum(d['count'] for d in days if int(d['date'][5:7])==m) for m in range(1,asof.month+1)]
    month_days=[sum(d['count']>0 for d in days if int(d['date'][5:7])==m) for m in range(1,asof.month+1)]
    bydate={d['date']:d for d in days};peak=max(days,key=lambda d:d['count'])
    weekday=[sum(d['count'] for d in days if dt.date.fromisoformat(d['date']).weekday()==w) for w in range(7)]
    start=asof-dt.timedelta(days=(asof.weekday()+1)%7+25*7)
    window=[d for d in days if str(start)<=d['date']]
    h_inventory=154
    lang=collections.Counter()
    for values in data.get('languages_by_repo',{}).values():lang.update(values)
    lang_total=sum(lang.values())
    community=data.get('community',{})
    colors={'dark':dict(bg='#0d1117',panel='#161b22',line='#30363d',text='#e6edf3',muted='#8b949e',blue='#58a6ff',green='#3fb950',violet='#bc8cff',zero='#21262d',levels=['#161b22','#0e4429','#006d32','#26a641','#39d353']),
            'light':dict(bg='#ffffff',panel='#f6f8fa',line='#d0d7de',text='#1f2328',muted='#656d76',blue='#0969da',green='#1a7f37',violet='#8250df',zero='#ebedf0',levels=['#ebedf0','#9be9a8','#40c463','#30a14e','#216e39'])}
    for theme,c in colors.items():
        def t(x,y,s,size=11,color='text',weight=400,anchor='start'):
            return f'<text x="{x}" y="{y}" fill="{c.get(color,color)}" font-size="{size}" font-weight="{weight}" text-anchor="{anchor}">{html.escape(str(s))}</text>'
        def line(x1,y1,x2,y2):return f'<path d="M{x1} {y1}H{x2}" stroke="{c["line"]}"/>' if y1==y2 else f'<path d="M{x1} {y1}L{x2} {y2}" stroke="{c["line"]}"/>'
        def rect(x,y,w,h,fill='bg',rx=5,stroke=True):
            return f'<rect x="{x+.5}" y="{y+.5}" width="{w-1}" height="{h-1}" rx="{rx}" fill="{c.get(fill,fill)}"'+(f' stroke="{c["line"]}"' if stroke else '')+'/>'
        def svg(name,height,content,width=920):
            s=f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-labelledby="title"><title id="title">{name} · public data · {data["as_of"]}</title><g font-family="Consolas,Menlo,DejaVu Sans Mono,monospace">{content}</g></svg>'
            (out/f'{name}-{theme}.svg').write_text(s,encoding='utf-8')

        content=rect(0,0,920,40,'panel')
        entries=[('STARS',stars,'#e3b341' if theme=='dark' else '#9a6700'),('FORKS',forks,'#f0883e' if theme=='dark' else '#bc4c00'),('DOWNLOADS',downloads,'blue'),('RELEASES',len(releases),'violet'),('CONTRIBUTIONS',total,'green'),('ACTIVE DAYS',active,'#f778ba' if theme=='dark' else '#bf3989')]
        for i,(label,n,color) in enumerate(entries):
            x=i*920/6
            content+=t(x+10,25,label,9,'muted')+t(x+920/6-10,27,f'{n:,}',17,color,600,'end')
            if i:content+=line(x,8,x,32)
        svg('overview',40,content)

        content=rect(0,0,920,236)+line(562,0,562,236)+rect(0,0,562,30,'panel',5,False)+rect(563,0,357,30,'panel',5,False)
        content+=t(13,20,'ACTIVITY / 26 WEEKS',11,'text',600)+t(548,20,f'{sum(d["count"] for d in window):,} contributions',10,'green',anchor='end')+t(576,20,f'MONTHLY / {year}',11,'text',600)
        last_month=None
        for d in window:
            date=dt.date.fromisoformat(d['date']);col=(date-start).days//7;row=(date.weekday()+1)%7;x=43+col*19;y=60+row*14
            if row==0 and date.day<=7:
                content+=t(x,48,calendar.month_abbr[date.month],10,'muted');last_month=date.month
            content+=f'<rect x="{x}" y="{y}" width="15" height="10" rx="2" fill="{c["levels"][d["level"]]}"><title>{d["date"]}: {d["count"]}</title></rect>'
        for row,name in [(1,'M'),(3,'W'),(5,'F')]:content+=t(15,68+row*14,name,9,'muted')
        content+=line(13,166,549,166)
        values=[('Current streak',f'{current}d'),('Longest streak',f'{longest}d'),('Peak day',peak['count']),('Active rate',f'{active/len(days)*100:.1f}%'),('Daily avg',f'{total/len(days):.2f}'),('Active-day avg',f'{total/(active or 1):.2f}')]
        for i,(label,val) in enumerate(values):
            x=13+(i%3)*181;y=188+(i//3)*27
            content+=t(x,y,label,10,'muted')+t(x+167,y,val,12,'blue',600,'end')
        content+=t(576,48,'MTH',10,'muted')+t(706,48,'COUNT',10,'muted',anchor='end')+t(795,48,'DAYS',10,'muted',anchor='end')+t(905,48,'SHARE',10,'muted',anchor='end')
        for i,n in enumerate(months):
            y=66+i*16
            if i%2==0:content+=rect(570,y-11,343,16,'panel',0,False)
            content+=t(576,y,calendar.month_abbr[i+1],11,'muted')+t(706,y,f'{n:,}',11,'text',500,'end')+t(795,y,month_days[i],11,'muted',anchor='end')+t(905,y,f'{n/(total or 1)*100:.1f}%',11,'blue',anchor='end')
        svg('activity',236,content)

        content=rect(0,0,452,180)+rect(468,0,452,180)+rect(0,0,452,29,'panel',5,False)+rect(468,0,452,29,'panel',5,False)
        content+=t(13,20,'COMMUNITY / AUTHORED',11,'text',600)+t(481,20,'LANGUAGES / ORIGINAL REPOS',11,'text',600)
        issues=community.get('issues_open',0)+community.get('issues_closed',0)
        prs=sum(community.get(k,0) for k in ['prs_open','prs_merged','prs_closed_unmerged'])
        for y,label,total_n,segments in [(49,'Issues',issues,[(community.get('issues_open',0),'Open','green'),(community.get('issues_closed',0),'Closed','violet')]),(112,'Pull requests',prs,[(community.get('prs_open',0),'Open','green'),(community.get('prs_merged',0),'Merged','violet'),(community.get('prs_closed_unmerged',0),'Closed','#f85149')])]:
            content+=t(13,y,label,12,'blue')+t(439,y,f'{total_n} total',10,'muted',anchor='end')
            x=13
            content+=rect(13,y+9,426,7,'zero',3,False)
            for j,(n,name,color) in enumerate(segments):
                w=426*n/(total_n or 1)
                if w:content+=f'<rect x="{x}" y="{y+9}" width="{w}" height="6" fill="{c.get(color,color)}"/>'
                x+=w
                content+=t(13+j*142,y+35,f'{n} {name}',10,color)
        content+=t(13,169,'PUBLIC / ALL TIME',9,'muted')+t(439,169,f'{community.get("prs_merged",0)/(prs or 1)*100:.1f}% merged',10,'violet',anchor='end')
        lang_colors={'Python':'#3572a5','Rust':'#dea584','C++':'#f34b7d','HTML':'#e34c26','PowerShell':'#012456','CMake':'#DA3434'}
        x=481
        sorted_lang=lang.most_common()
        for name,n in sorted_lang:
            w=426*n/(lang_total or 1)
            content+=f'<rect x="{x}" y="41" width="{w}" height="7" fill="{lang_colors.get(name,c["blue"])}"/>';x+=w
        for i,(name,n) in enumerate(sorted_lang[:6]):
            x=481+(i%2)*221;y=73+(i//2)*31
            content+=f'<circle cx="{x+3}" cy="{y-4}" r="3" fill="{lang_colors.get(name,c["blue"])}"/>'+t(x+13,y,name,10,'text')+t(x+205,y,f'{n/(lang_total or 1)*100:.2f}%',10,'blue',anchor='end')
            size=f'{n/1048576:.2f} MiB' if n>=1048576 else f'{n/1024:.1f} KiB'
            content+=t(x+13,y+13,size,9,'muted')
        content+=t(481,169,f'{len(owned)} repos / {lang_total/1048576:.2f} MiB / byte share',9,'muted')
        svg('insights',180,content)

    from compact_cards import render as render_platform_cards
    render_platform_cards(data,root)
    return {'stars':stars,'forks':forks,'original_repos':len(owned),'forked_repos':len(repos)-len(owned),'downloads':downloads,'releases':len(releases),'contributions_ytd':total,'active_days':active,'current_streak':current,'longest_streak':longest,'months':months,'weekday_contributions':weekday,'days_displayed':len(window),'featured_rows':min(2,len(owned)),'release_rows':min(3,len(releases)),'languages':len(lang),'language_bytes':lang_total,'steam_connected':bool(data.get('steam')),'bangumi_anime_total':data.get('bangumi',{}).get('total'),'platform_layout':'2-2-3-3 / Bilibili, Steam, Bangumi','star_timestamps':data.get('star_growth',{}).get('total'),'bilibili_followers':data.get('bilibili',{}).get('followers')}
