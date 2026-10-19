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

The workflow is configured for 01:19 UTC / 09:19 Beijing daily and manual dispatch.
Enable Actions, allow workflow write permissions, and manually run **Refresh profile stats**
once to verify the hosted environment. Schedules can be delayed by GitHub.
Only the built-in `GITHUB_TOKEN` is used; never upload login cookies or personal credentials.
Local rendering has been verified; the hosted collection workflow has not run yet.

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
- Steam / Bangumi / Bilibili collection failures preserve previous values and dates,
  with `refresh_status: stale` in the snapshot. API changes and rate limits may affect refresh.
- Avatars are cached assets; the daily workflow does not refresh them.
- Steam and Bilibili bottom stripes are decorative, not proportions.

The 2-2-3-3 layout, compact English labels, and subtle pink / mauve / purple platform
headers are intentional. Previous drafts and review artifacts do not belong in this repository.
