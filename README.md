# Le Programme

The latest long videos (no Shorts, no lives) from a short list of YouTube channels,
on one page: https://corbiiy.github.io/yt-checker/

- `channels.txt` lists the channels, one per line (`@handle`, a channel URL or a `UC…` id).
  Edit it on GitHub to add or remove one; the page updates a minute or two after the commit.
- `.github/workflows/check.yml` runs `fetch.py`, commits `data/state.json` when the video
  list changes, and deploys `site/` to GitHub Pages. It runs on every push and whenever
  `railway-trigger/` starts it.
- `railway-trigger/` is a Railway cron service (project "Le Programme", service "trigger")
  that starts the workflow every 30 minutes from 15:04 to 23:34, Paris time. Its schedule,
  `4,34 13-22 * * *` in UTC, is set in the service settings, and `trigger.sh` skips the
  slots before 15:00 Paris, so summer time needs no change (`CHECK_FROM` in
  `site/index.html` must match). It needs a `GITHUB_TOKEN` variable: a fine-grained token
  with "Actions: read and write" on this repository only. GitHub's own `schedule:` trigger
  never ran here, which is why the start comes from Railway.
- `fetch.py` reads each channel's "UULF" playlist feed, which is the Videos tab without
  Shorts and live streams. It needs only the Python standard library.
- The page marks videos as **Nouveau** when this browser hadn't seen them at the start of
  the visit (a visit ends after 30 minutes away). On a first visit, the last 48 hours count.

Run it locally:

```bash
python3 -m unittest -v
SSL_CERT_FILE=/etc/ssl/cert.pem python3 fetch.py   # the cert path is only needed with python.org's Python on macOS
python3 -m http.server 8790 --directory site
```
