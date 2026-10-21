"""Two rows of three independent cards, 296 x 144. Never fabricate platform stats."""
import base64
import html
from refresh_state import label as date_label, description, is_stale


def render(data, root):
    assets = root / 'assets' / 'cards'
    assets.mkdir(parents=True, exist_ok=True)
    owned = sorted([r for r in data['repos'] if not r['fork']], key=lambda r: -r['stargazers_count'])[:2]
    releases = sorted([r for r in data['releases'] if not r.get('draft')], key=lambda r: r['published_at'], reverse=True)
    for theme in ['dark', 'light']:
        dark = theme == 'dark'
        bg = '#0d1117' if dark else '#ffffff'
        panel = '#161b22' if dark else '#f6f8fa'
        border = '#30363d' if dark else '#d0d7de'
        fg = '#e6edf3' if dark else '#1f2328'
        muted = '#8b949e' if dark else '#656d76'
        blue = '#58a6ff' if dark else '#0969da'
        purple = '#bc8cff' if dark else '#8250df'
        green = '#3fb950' if dark else '#1a7f37'

        def t(x, y, value, size=10, color=None, weight=400, anchor='start'):
            return f'<text x="{x}" y="{y}" fill="{color or fg}" font-size="{size}" font-weight="{weight}" text-anchor="{anchor}">{html.escape(str(value))}</text>'

        def save(name, content, gradient=None, defs='', title=None, body=None):
            module={'projects':'github','releases':'github','star-growth':'star_growth'}.get(name,name)
            title=(title or name)+' / '+description(data,module)
            banner = ''
            if gradient:
                a, b = gradient
                defs += f'<linearGradient id="banner" x2="1" y2="1"><stop stop-color="{a}"/><stop offset="1" stop-color="{b}"/></linearGradient>'
                banner = '<rect width="296" height="56" fill="url(#banner)"/>'
            svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="296" height="144" viewBox="0 0 296 144" role="img" aria-labelledby="title"><title id="title">{html.escape(title or name)}</title><defs><clipPath id="card"><rect x=".5" y=".5" width="295" height="143" rx="10"/></clipPath><clipPath id="avatar"><rect x="12" y="12" width="34" height="34" rx="10"/></clipPath>{defs}</defs><g clip-path="url(#card)" font-family="Segoe UI,Arial,sans-serif"><rect width="296" height="144" fill="{body or (bg if not gradient else panel)}"/>{banner}{content}</g><rect x=".5" y=".5" width="295" height="143" rx="10" fill="none" stroke="{border}"/></svg>'''
            (assets / f'{name}-{theme}.svg').write_text(svg, encoding='utf-8')

        def header(label, right=''):
            return f'<path d="M0 29H296V0H0Z" fill="{panel}"/>'+t(12, 19, label, 10, weight=600)+t(284, 19, right, 8, muted, anchor='end')

        def avatar(filename):
            encoded = base64.b64encode((root / 'assets' / 'avatars' / filename).read_bytes()).decode('ascii')
            return f'<image x="12" y="12" width="34" height="34" clip-path="url(#avatar)" href="data:image/jpeg;base64,{encoded}"/>'

        content = header('PROJECTS', f'{len(owned)} ORIGINALS')
        for i, repo in enumerate(owned):
            y = 51 + i * 49
            content += t(12, y, repo['name'], 11, blue, 600)
            content += t(12, y+18, f'{repo["stargazers_count"]} stars  /  {repo["forks_count"]} forks', 10)
            content += t(284, y+18, repo.get('language') or '—', 9, muted, anchor='end')
            if i == 0:
                content += f'<path d="M12 82H284" stroke="{border}"/>'
        content += t(12, 134, 'PUBLIC / NON-FORK', 8, muted)+t(284,134,date_label(data,'github'),8,muted,anchor='end')
        save('projects', content)

        content = header('RELEASES', 'LATEST 3')
        content += t(12, 45, 'VERSION', 8, muted)+t(136, 45, 'DATE', 8, muted)+t(284, 45, 'DOWNLOADS', 8, muted, anchor='end')
        for i, release in enumerate(releases[:3]):
            y = 65 + i * 24
            count = sum(a['download_count'] for a in release['assets'])
            content += t(12, y, release['tag_name'], 11, purple)+t(136, y, release['published_at'][5:10], 9, muted)+t(284, y, f'{count:,}', 11, weight=600, anchor='end')
        content += t(12, 134, 'NTE-DRIVE-CALCULATOR', 8, muted)+t(284,134,date_label(data,'github'),8,muted,anchor='end')
        save('releases', content)

        growth = data.get('star_growth')
        content = header('STAR GROWTH', date_label(data,'star_growth'))
        if growth:
            content += t(12, 57, growth['total'], 23, blue, 600)+t(65, 57, 'stars', 9, muted)
            content += t(284, 55, f'+{growth["received_30d"]} / 30d', 11, green, 600, 'end')
            points = growth['points_30d'];values = [p['count'] for p in points]
            low = max(0, min(values)-max(2, int((max(values)-min(values))*.15)))
            high = max(max(values), low+1)
            coords = [(12+i*272/(len(values)-1), 112-(v-low)/(high-low)*42) for i,v in enumerate(values)]
            path = 'M'+' L'.join(f'{x:.2f} {y:.2f}' for x,y in coords)
            content += f'<path d="{path} L284 114H12Z" fill="{blue}" opacity=".10"/><path d="M12 114H284" stroke="{border}"/><path d="{path}" fill="none" stroke="{blue}" stroke-width="2" stroke-linejoin="round"/>'
            x, y = coords[-1]
            content += f'<circle cx="{x}" cy="{y}" r="2.5" fill="{blue}"/>'
            content += t(12, 131, f'{points[0]["date"][5:]} / {values[0]}', 8, muted)+t(284, 131, f'{points[-1]["date"][5:]} / {values[-1]}', 8, muted, anchor='end')
        else:
            content += t(12, 77, 'Star timestamps pending', 12, muted)
        save('star-growth', content, title='Star Growth / reconstructed from currently retained stars, not historical net totals')

        steam = data['steam'];accent = '#d0accb' if dark else '#a05f94'
        content = avatar('steam-avatar.jpg')+t(58, 25, 'STEAM', 10, accent, 700)+t(58, 43, steam['name'], 14, weight=600)+t(284, 25, '↗', 14, muted, anchor='end')
        content += t(284, 43, date_label(data,'steam'), 8, muted, anchor='end')
        for i, (label, value) in enumerate([('GAMES',steam['games']),('LEVEL',steam['level']),('BADGES',steam['badges']),('JOINED',steam['member_since'][-4:])]):
            x = 12+i*69
            if i:
                content += f'<path d="M{x-8} 73v40" stroke="{border}"/>'
            content += t(x, 94, value, 23, accent if i==0 else fg, 600)+t(x, 112, label, 8, muted, 600)
        defs='<linearGradient id="accent"><stop stop-color="#ce9ab8"/><stop offset=".5" stop-color="#b795c8"/><stop offset="1" stop-color="#a5a0da"/></linearGradient>'
        content += '<g aria-label="Decorative accent, not a statistic"><title>Decorative accent, not a statistic</title><rect x="12" y="128" width="272" height="4" rx="2" fill="url(#accent)"/></g>'
        save('steam', content, ('#352938','#24202b') if dark else ('#f0e6ef','#f9f4f8'), defs)

        bgm = data['bangumi'];counts=bgm['counts'];accent='#d6a7ff' if dark else '#8250df'
        content=avatar('bangumi-avatar.jpg')+t(58,25,'BANGUMI',10,accent,700)+t(58,43,bgm['username'],12,weight=600)
        content+=t(284,27,f'{bgm["total"]} ANIME',13,accent,600,'end')+t(284,43,'STALE' if is_stale(data,'bangumi') else f'{counts["2"]/(bgm["total"] or 1):.0%} completed',8,muted,anchor='end')
        xbar=12
        for i,(key,label,color) in enumerate([('2','COMPLETED','#a371f7'),('3','WATCHING','#3fb950'),('1','PLANNED','#58a6ff'),('4','ON HOLD','#d29922'),('5','DROPPED','#8b949e')]):
            x=12+i*55
            content+=t(x,91,counts[key],21,weight=600)+t(x,111,label,7,muted,600)
            width=272*counts[key]/(bgm['total'] or 1)
            content+=f'<rect x="{xbar}" y="128" width="{width}" height="4" fill="{color}"/>';xbar+=width
        content+=t(284,141,date_label(data,'bangumi'),7,muted,anchor='end')
        save('bangumi',content,('#392d44','#201c30') if dark else ('#f0e5f5','#f7f3fc'))

        bili=data['bilibili'];accent='#f47ca9' if dark else '#b33c6f'
        content=avatar('bilibili-avatar.jpg')+t(58,25,'BILIBILI',10,accent,700)+t(58,43,'UID '+bili['uid'],11,weight=600)
        content+=t(284,25,'LV.'+str(bili['level']),9,accent,600,'end')+t(284,43,date_label(data,'bilibili'),8,muted,anchor='end')
        for i,(label,key) in enumerate([('FOLLOWERS','followers'),('FOLLOWING','following'),('VIDEOS','videos'),('LIKES','likes')]):
            x=12+i*69;value=bili[key]
            number=f'{value:,}' if value<100000 else (f'{value/1000000:.1f}m' if value>=1000000 else f'{value/1000:.1f}k')
            if i:content+=f'<path d="M{x-8} 73v40" stroke="{border}"/>'
            content+=t(x,94,number,19,accent if i==0 else fg,600)+t(x,112,label,7.5,muted,600)
        defs='<linearGradient id="bili-accent"><stop stop-color="#f47ca9"/><stop offset=".5" stop-color="#c18cf0"/><stop offset="1" stop-color="#71b7ed"/></linearGradient>'
        content+='<g aria-label="Decorative accent, not a statistic"><title>Decorative accent, not a statistic</title><rect x="12" y="128" width="272" height="4" rx="2" fill="url(#bili-accent)"/></g>'
        save('bilibili',content,('#35232e','#241e29') if dark else ('#f7e8ef','#faf5f8'),defs,title='Bilibili / anonymous public metrics / '+bili['as_of'])
