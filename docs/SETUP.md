# Profile repository

## Structure

```text
README.md                     GitHub profile entry
.github/workflows/            Scheduled data refresh
assets/cards/                 Generated dark/light SVGs
assets/avatars/               Cached public avatars embedded in SVGs
data/stats.json               Latest public-data snapshot
scripts/                      Collectors and SVG renderers (Python standard library)
preview/index.html            Clickable local preview with theme switch
tests/                        Offline regression tests
```

## Local preview and checks

Python 3.10+ is sufficient; no pip packages or platform login required.

```sh
python -B scripts/update_stats.py --snapshot data/stats.json
python -B -m unittest discover -s tests -v
python -m http.server 8000
```

Open http://localhost:8000/preview/ . This is a local approximation, not a GitHub screenshot.
The three platform cards link to Bilibili, Steam and Bangumi respectively.

## Publish

Create the public profile repository `hxwd94666/hxwd94666`, then upload this
directory's contents (including `.github`). No Git repository has been created
or uploaded by this local cleanup.

The workflow runs at UTC 01:19 / 07:19 / 13:19 / 19:19 (Beijing 09:19 /
15:19 / 21:19 / next-day 03:19). GitHub may delay scheduled runs.
Enable Actions and allow workflow write permissions. Only the built-in
`GITHUB_TOKEN` is used; never upload login cookies or personal credentials.

## Refresh behavior

- Freshness is checked separately for GitHub statistics, community, Star Growth,
  Steam, Bangumi and Bilibili, using each module's own data date (Asia/Shanghai).
  Scheduled runs fetch only missing, older or failed modules; all fresh means no requests.
- Run **Actions → Refresh profile stats → Run workflow** with **force** checked
  (default) to refresh every module even on the same day. Uncheck it to retry only
  due modules. Local equivalents: `python -B scripts/update_stats.py --force`
  and `python -B scripts/update_stats.py`.
- Star Growth shares the current run's repository list, or fetches a new list when
  it alone needs a retry. It never validates new timestamps against cached star counts.
  GitHub and Star Growth are separate samples, so same-day counts can differ.
- On failure, keep that module's verified values and original data date. Record
  `refresh.<module>.status`, `attempted_at` (UTC) and `error` in `data/stats.json`
  and print the reason in the Actions log; known bearer tokens are redacted.
  Other modules continue. A usable partial refresh can finish successfully: check
  the per-module status, not just the workflow's green checkmark.
- Cards display **AS OF YYYY-MM-DD**, or **STALE / YYYY-MM-DD** after a failed
  refresh. SVG titles include the recorded reason. A successful retry clears the
  old error. No baseline on first collection means generation stops rather than
  inventing values.
- `--snapshot` is offline rendering only: it neither fetches nor changes data dates.

Related checks (no network):

```sh
python -B -m unittest discover -s tests -p "test_refresh.py" -v
python -B -m unittest discover -s tests -p "test_profile.py" -k "render" -v
```

## Data definitions

- Snapshot images are not real-time presence. Dates belong to their source snapshot.
- GitHub Stars / Forks / Languages: owned public non-fork repositories.
- Contributions / active days / streaks: public contribution calendar, year to date;
  contributions are not synonymous with commits. Activity grid shows 26 weeks.
- Community: public issues and PRs authored by this account, all-time status.
- Languages: repository language bytes, not skill proficiency.
- Releases / downloads: published NTE-Drive-Calculator release assets, cumulative
  download requests rather than unique people. Only the latest three releases are listed.
- Star Growth: reconstruction from currently retained stargazer timestamps, not a full
  history of gained and lost stars. The 30-day value excludes removed stars.
- Bilibili: public followers, following, videos, likes and level, without login.
- Steam: game count, level, badges and joined year; no playtime.
- Bangumi: public anime collections only; completed share = completed / total.
- Collection failures preserve previous values and dates with per-module stale status.
  Existing `refresh_status: stale` flags are also recognized. API changes and rate limits
  may affect refresh.
- Avatars are cached assets; the daily workflow does not refresh them.
- Steam and Bilibili bottom stripes are decorative, not proportions.

The 2-2-3-3 layout, compact English labels, and subtle pink / mauve / purple platform
headers are intentional. Previous drafts and review artifacts do not belong in this repository.
