"""Focused offline regressions for refresh decisions, isolation and visible dates."""
import copy
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import refresh_state as state
import update_stats as updater


class RefreshTests(unittest.TestCase):
    def setUp(self):
        self.today = '2026-10-21'
        self.data = json.loads((ROOT / 'data/stats.json').read_text(encoding='utf-8'))
        self.data['as_of'] = self.data['community_as_of'] = self.today
        self.data.pop('refresh', None)
        for name in state.MODULES[2:]:
            self.data[name]['as_of'] = self.today
            self.data[name].pop('refresh_status', None)
            self.data[name].pop('refresh_error', None)

    def run_collect(self, data, force=False, failed=None):
        github = {k: copy.deepcopy(self.data[k]) for k in state.GITHUB_FIELDS}
        github['as_of'] = self.today
        targets = {'github': 'update_stats.collect_github',
                   'community': 'update_stats.collect_community',
                   'star_growth': 'star_growth.collect', 'steam': 'steam_profile.collect',
                   'bangumi': 'bangumi_profile.collect', 'bilibili': 'bilibili_profile.collect'}
        from contextlib import ExitStack
        with ExitStack() as stack:
            calls = {}
            repo_call = stack.enter_context(patch('update_stats.collect_repos', return_value=self.data['repos']))
            for module, target in targets.items():
                value = github if module == 'github' else self.data[module]
                calls[module] = stack.enter_context(patch(target, return_value=copy.deepcopy(value)))
            if failed:
                calls[failed].side_effect = RuntimeError('offline fixture')
            result = updater.collect(data, force=force, today=self.today)
        return result, calls, repo_call

    def test_freshness_is_per_module_and_force_overrides(self):
        self.assertEqual(state.due_modules(self.data, self.today), [])
        self.data['star_growth']['as_of'] = '2026-10-19'
        self.assertEqual(state.due_modules(self.data, self.today), ['star_growth'])
        self.data['star_growth']['as_of'] = self.today
        self.data['star_growth']['refresh_status'] = 'stale'
        self.assertEqual(state.due_modules(self.data, self.today), ['star_growth'])
        self.data['refresh'] = {'community': {'status': 'stale', 'error': 'fixture'}}
        self.assertEqual(state.due_modules(self.data, self.today), ['community', 'star_growth'])
        self.assertEqual(state.due_modules(self.data, self.today, True), list(state.MODULES))
        del self.data['steam']
        self.assertIn('steam', state.due_modules(self.data, self.today))

    def test_fresh_modules_make_no_requests(self):
        result, calls, repos = self.run_collect(self.data)
        self.assertEqual(result, self.data)
        for call in [repos, *calls.values()]:
            call.assert_not_called()

    def test_star_only_retry_uses_live_counts_not_cached_counts(self):
        # Retrying an old series must not perpetually compare new stars to old totals.
        self.data['star_growth']['refresh_status'] = 'stale'
        old = copy.deepcopy(self.data)
        old['repos'][0]['stargazers_count'] += 99
        result, calls, repos = self.run_collect(old)
        repos.assert_called_once_with()
        self.assertEqual(calls['star_growth'].call_args.args[0], self.data['repos'])
        self.assertEqual(result['repos'], old['repos'])  # Independent GitHub sample is untouched.
        self.assertNotIn('refresh_status', result['star_growth'])
        self.assertEqual(result['refresh']['star_growth']['status'], 'fresh')
        for name in state.MODULES:
            if name != 'star_growth':calls[name].assert_not_called()

    def test_failure_preserves_each_module_and_recovery_clears_error(self):
        for module in state.MODULES:
            with self.subTest(module=module):
                prior = copy.deepcopy(self.data)
                if module == 'github':prior['as_of'] = '2026-10-19'
                elif module == 'community':prior['community_as_of'] = '2026-10-19'
                else:prior[module]['as_of'] = '2026-10-19'
                original = copy.deepcopy(prior)
                result, calls, _ = self.run_collect(prior, force=True, failed=module)
                keys = (*state.GITHUB_FIELDS, 'as_of') if module == 'github' else ((module, 'community_as_of') if module == 'community' else (module,))
                for key in keys:self.assertEqual(result[key], original[key])
                self.assertEqual(prior, original)  # No mutation of the last verified snapshot.
                self.assertEqual(result['refresh'][module]['status'], 'stale')
                self.assertEqual(result['refresh'][module]['error'], 'RuntimeError: offline fixture')
                self.assertTrue(result['refresh'][module]['attempted_at'])
                for call in calls.values():call.assert_called_once()
                self.assertEqual(state.due_modules(result, self.today), [module])
                recovered, retry_calls, _ = self.run_collect(result)
                self.assertEqual(recovered['refresh'][module]['status'], 'fresh')
                self.assertNotIn('error', recovered['refresh'][module])
                self.assertEqual(state.due_modules(recovered, self.today), [])
                retry_calls[module].assert_called_once()

    def test_force_refreshes_all_and_shares_live_repositories(self):
        self.assertEqual(state.due_modules(self.data, self.today), [])
        result, calls, repos = self.run_collect(self.data, force=True)
        for call in calls.values():call.assert_called_once()
        repos.assert_called_once_with()
        self.assertEqual(state.due_modules(result, self.today), [])
        for value in result['refresh'].values():self.assertNotIn('error', value)

    def test_cli_gate_and_update_respect_root_and_force(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'data').mkdir()
            data = copy.deepcopy(self.data)
            today = state.today_local()
            data['as_of'] = data['community_as_of'] = today
            for name in state.MODULES[2:]:data[name]['as_of'] = today
            path = root / 'data/stats.json'
            path.write_text(json.dumps(data), encoding='utf-8')
            command = [sys.executable, '-B', str(ROOT / 'scripts/check_fresh_today.py'), '--root', temp]
            fresh = subprocess.run(command, capture_output=True, text=True)
            forced = subprocess.run(command + ['--force'], capture_output=True, text=True)
            self.assertEqual(fresh.returncode, 0, fresh.stderr)
            self.assertEqual(forced.returncode, 1, forced.stderr)
            data['star_growth']['refresh_status'] = 'stale'
            path.write_text(json.dumps(data), encoding='utf-8')
            stale = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(stale.returncode, 1, stale.stderr)
            self.assertIn('due=star_growth', stale.stdout)
            with patch.object(sys, 'argv', ['update_stats.py', '--root', temp, '--force']), patch.object(updater, 'collect', return_value=data) as collect, patch.object(updater, 'render', return_value={}):
                updater.main()
            collect.assert_called_once_with(data, force=True)
            self.assertEqual(json.loads(path.read_text(encoding='utf-8')), data)

    def test_cards_show_source_dates_and_escaped_failure_reason(self):
        from dense_cards import render
        data = copy.deepcopy(self.data)
        data['community_as_of'] = '2026-10-18'
        data['refresh'] = {m: {'status': 'stale', 'error': 'API <fixture> & retry'} for m in state.MODULES}
        data['star_growth']['as_of'] = '2026-10-19'
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            shutil.copytree(ROOT / 'assets/avatars', root / 'assets/avatars')
            render(data, root)
            for svg in (root / 'assets/cards').glob('*.svg'):
                element = ET.parse(svg).getroot()
                title = element.find('{http://www.w3.org/2000/svg}title').text
                visible = ' '.join(e.text or '' for e in element.iter('{http://www.w3.org/2000/svg}text'))
                self.assertIn('STALE / ', visible, svg.name)
                self.assertIn('API <fixture> & retry', title, svg.name)
                stamp = '2026-10-19' if svg.name.startswith('star-growth') else self.today
                self.assertIn(stamp, visible, svg.name)
                if svg.name.startswith('insights'):self.assertIn('2026-10-18', visible)

    def test_published_errors_redact_credentials(self):
        with patch.dict(os.environ, {'GH_TOKEN': 'fixture-token', 'GITHUB_TOKEN': 'fixture-other'}):
            reason = state.error_reason(RuntimeError('fixture-token fixture-other Bearer another-secret'))
        self.assertNotIn('fixture-token', reason)
        self.assertNotIn('fixture-other', reason)
        self.assertNotIn('another-secret', reason)
        self.assertIn('RuntimeError:', reason)
        self.assertEqual(len(state.error_reason(RuntimeError('x' * 1000))), 500)


class StarHistoryTests(unittest.TestCase):
    def test_public_history_pagination_and_daily_totals(self):
        import datetime as dt
        from star_growth import collect
        from unittest.mock import Mock
        newest = dt.datetime(2026, 10, 18, tzinfo=dt.timezone.utc)
        rows = []
        for i in range(31):
            counts = [2, 0, 3, 0, 0, 0, 0] if i == 0 else [1, 0, 0, 0, 0, 0, 0]
            rows.append({'week': int((newest - dt.timedelta(weeks=i)).timestamp()), 'days': counts, 'total': sum(counts)})
        get = Mock(side_effect=[rows[:30], rows[30:], []])
        repos = [{'name': 'repo', 'full_name': 'owner/repo', 'fork': False, 'stargazers_count': 35},
                 {'name': 'empty', 'full_name': 'owner/empty', 'fork': False, 'stargazers_count': 0},
                 {'name': 'fork', 'full_name': 'owner/fork', 'fork': True, 'stargazers_count': 999}]
        actual = collect(repos, '2026-10-21', get)
        self.assertEqual(actual['total'], 35)
        self.assertEqual(actual['received_30d'], 8)
        self.assertEqual(actual['points_30d'][0], {'date': '2026-09-22', 'count': 27})
        self.assertEqual(actual['points_30d'][-1], {'date': '2026-10-21', 'count': 35})
        self.assertEqual(len(actual['points_30d']), 30)
        self.assertEqual(actual['daily_by_repo']['empty'], {})
        self.assertEqual(actual['basis'], 'public_aggregate_star_history')
        self.assertEqual(get.call_count, 3)
        for call in get.call_args_list:
            self.assertIn('/stargazers/history?per_page=30&page=', call.args[0])
            self.assertEqual(call.kwargs, {'authenticated': False})
        self.assertIn('page=2', get.call_args_list[1].args[0])

    def test_invalid_or_denied_history_preserves_verified_series(self):
        from star_growth import refresh
        from urllib.error import HTTPError
        from unittest.mock import Mock
        prior = json.loads((ROOT / 'data/stats.json').read_text(encoding='utf-8'))['star_growth']
        original = copy.deepcopy(prior)
        valid = {'week': 1792281600, 'total': 1, 'days': [1, 0, 0, 0, 0, 0, 0]}
        cases = [[dict(valid, days=[1])], [dict(valid, total=2)], [valid, valid],
                 [dict(valid, total=0, days=[0]*7)], HTTPError('https://api.github.com/history', 403, 'Forbidden', {}, None)]
        for case in cases:
            with self.subTest(case=type(case).__name__):
                get = Mock(side_effect=case) if isinstance(case, Exception) else Mock(return_value=case)
                result = refresh([{'name': 'repo', 'full_name': 'owner/repo', 'fork': False, 'stargazers_count': 1}], '2026-10-21', get, prior)
                for key, value in prior.items():self.assertEqual(result[key], value)
                self.assertEqual(result['refresh_status'], 'stale')
                self.assertTrue(result['refresh_error'])
                self.assertEqual(prior, original)

    def test_public_history_request_omits_authorization(self):
        from unittest.mock import MagicMock
        response = MagicMock()
        response.__enter__.return_value.read.return_value = b'[]'
        with patch.dict(os.environ, {'GH_TOKEN': 'fixture-token'}), patch.object(updater, 'urlopen', return_value=response) as open_url:
            self.assertEqual(updater.get('https://api.github.com/history', authenticated=False), [])
            self.assertFalse(open_url.call_args.args[0].has_header('Authorization'))
            updater.get('https://api.github.com/repos/owner/repo')
            self.assertEqual(open_url.call_args.args[0].get_header('Authorization'), 'Bearer fixture-token')


if __name__ == '__main__':unittest.main()
