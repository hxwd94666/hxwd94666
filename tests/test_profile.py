import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))

class ProfileTests(unittest.TestCase):
    def test_local_links_and_platform_order(self):
        for name in ('README.md', 'preview/index.html'):
            path = ROOT / name
            text = path.read_text(encoding='utf-8')
            for link in re.findall(r'(?:src|srcset)="([^"#]+)"', text):
                self.assertTrue((path.parent / link).is_file(), link)
            urls = ['https://space.bilibili.com/436632831', 'https://steamcommunity.com/profiles/76561198402274250/', 'https://bgm.tv/user/hxwd94666']
            positions = [text.index(url) for url in urls]
            self.assertEqual(positions, sorted(positions))
            self.assertNotIn('support on Afdian', text)
            self.assertNotIn('xiaoheihe', text)
            self.assertNotIn('y.qq.com', text)
        self.assertIn("p.src='../assets/cards/'", (ROOT / 'preview/index.html').read_text(encoding='utf-8'))

    def test_cards_and_colors(self):
        self.assertEqual(len(list((ROOT / 'assets/cards').glob('*.svg'))), 18)
        for theme in ('dark', 'light'):
            for name in ('projects', 'releases', 'star-growth', 'bilibili', 'steam', 'bangumi'):
                xml = ET.parse(ROOT / 'assets/cards' / f'{name}-{theme}.svg').getroot()
                self.assertEqual((xml.get('width'), xml.get('height')), ('296', '144'))
            for name, size in (('overview', ('920', '40')), ('activity', ('920', '236')), ('insights', ('920', '180'))):
                xml = ET.parse(ROOT / 'assets/cards' / f'{name}-{theme}.svg').getroot()
                self.assertEqual((xml.get('width'), xml.get('height')), size)
        for name, color in [('bilibili', '#35232e'), ('steam', '#352938'), ('bangumi', '#392d44')]:
            self.assertIn(color, (ROOT / 'assets/cards' / f'{name}-dark.svg').read_text(encoding='utf-8'))

    def test_offline_render_is_reproducible(self):
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp)
            shutil.copytree(ROOT / 'assets/avatars', target / 'assets/avatars')
            result = subprocess.run([sys.executable, '-B', str(ROOT / 'scripts/update_stats.py'), '--snapshot', str(ROOT / 'data/stats.json'), '--root', str(target)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            for source in (ROOT / 'assets/cards').glob('*.svg'):
                self.assertEqual(source.read_bytes(), (target / 'assets/cards' / source.name).read_bytes(), source.name)
            self.assertEqual(json.loads((ROOT / 'data/stats.json').read_text(encoding='utf-8')), json.loads((target / 'data/stats.json').read_text(encoding='utf-8')))

    def test_render_platform_dates_align(self):
        from compact_cards import render
        from refresh_state import label
        data = json.loads((ROOT / 'data/stats.json').read_text(encoding='utf-8'))
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            shutil.copytree(ROOT / 'assets/avatars', root / 'assets/avatars')
            for status in ('fresh', 'stale'):
                for name in ('bilibili', 'steam', 'bangumi'):
                    data.setdefault('refresh', {})[name] = {'status': status}
                render(data, root)
                for theme in ('dark', 'light'):
                    for name in ('bilibili', 'steam', 'bangumi'):
                        with self.subTest(status=status, theme=theme, platform=name):
                            svg = ET.parse(root / 'assets/cards' / f'{name}-{theme}.svg').getroot()
                            texts = list(svg.iter('{http://www.w3.org/2000/svg}text'))
                            dates = [e for e in texts if data[name]['as_of'] in (e.text or '')]
                            self.assertEqual(len(dates), 1)
                            self.assertEqual(dates[0].text, label(data, name))
                            self.assertEqual((dates[0].get('x'), dates[0].get('y'), dates[0].get('font-size'), dates[0].get('text-anchor')), ('284', '43', '8', 'end'))
                            if name == 'bangumi':
                                self.assertFalse(any('completed' in (e.text or '') for e in texts))

    def test_render_releases_by_total_downloads(self):
        from compact_cards import render
        data = json.loads((ROOT / 'data/stats.json').read_text(encoding='utf-8'))
        def release(tag, day, counts, draft=False):
            return {'tag_name': tag, 'published_at': '2026-10-'+day+'T00:00:00Z', 'draft': draft,
                    'assets': [{'download_count': count} for count in counts]}
        data['releases'] = [release('newest', '21', [10]), release('older', '01', [180]),
                            release('alpha', '02', [180]), release('popular', '01', [100, 100]),
                            release('beta', '02', [180]), release('draft', '21', [9999], True)]
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            shutil.copytree(ROOT / 'assets/avatars', root / 'assets/avatars')
            render(data, root)
            for theme in ('dark', 'light'):
                svg = ET.parse(root / 'assets/cards' / f'releases-{theme}.svg').getroot()
                texts = [e for e in svg.iter('{http://www.w3.org/2000/svg}text')]
                tags = [e.text for e in texts if e.get('x')=='12' and e.get('y') in ('65', '89', '113')]
                counts = [e.text for e in texts if e.get('x')=='284' and e.get('y') in ('65', '89', '113')]
                self.assertEqual(tags, ['popular', 'beta', 'alpha'])
                self.assertEqual(counts, ['200', '180', '180'])
                self.assertIn('TOP 3 DOWNLOADS', [e.text for e in texts])

    def test_failed_public_fetch_preserves_values(self):
        from bilibili_profile import refresh
        prior = json.loads((ROOT / 'data/stats.json').read_text(encoding='utf-8'))['bilibili']
        def failed(): raise RuntimeError('offline fixture')
        actual = refresh(prior, fetch=failed)
        self.assertEqual(actual, dict(prior, refresh_status='stale', refresh_error='RuntimeError: offline fixture'))
        self.assertNotIn('refresh_status', prior)

    def test_failed_star_growth_fetch_preserves_values(self):
        from star_growth import refresh
        prior = json.loads((ROOT / 'data/stats.json').read_text(encoding='utf-8'))['star_growth']
        def failed(*args, **kwargs): raise RuntimeError('API rate limit fixture')
        repos = [{'full_name': 'owner/repo', 'name': 'repo', 'fork': False, 'stargazers_count': 1}]
        actual = refresh(repos, '2026-10-19', failed, previous=prior)
        self.assertEqual(actual, dict(prior, refresh_status='stale', refresh_error='RuntimeError: API rate limit fixture'))

if __name__ == '__main__': unittest.main()
