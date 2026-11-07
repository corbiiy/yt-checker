# Le Programme

The latest long videos (no Shorts, no lives) from a short list of YouTube channels,
on one page: https://corbiiy.github.io/yt-checker/

- `channels.txt` lists the channels, one per line (`@handle`, a channel URL or a `UC…` id).
  Edit it on GitHub to add or remove one; the page updates a minute or two after the commit.
- `.github/workflows/check.yml` runs `fetch.py`, commits `data/state.json` when the video
  list changes, and deploys `site/` to GitHub Pages. It runs on every push and whenever
  `railway-trigger/` starts it.
- `railway-trigger/` is a Railway cron service (project "Le Programme", service "trigger")
  that starts the workflow every 30 minutes until 23:34, Paris time: from 15:04 on weekdays
  and from 9:04 at the weekend. Its schedule, `4,34 7-22 * * *` in UTC, is set in the
  service settings, and `trigger.sh` skips the slots before that day's start hour in Paris,
  so summer time needs no change (`CHECK_FROM` in `site/index.html` must match). It needs a `GITHUB_TOKEN` variable: a fine-grained token
  with "Actions: read and write" on this repository only. GitHub's own `schedule:` trigger
  never ran here, which is why the start comes from Railway.
- `railway-button/` is a small Railway web service (service "button",
  `https://button-production-2f62.up.railway.app`) behind the page's **Vérifier maintenant**
  button. `POST /check` starts the workflow at most once every 2 minutes (a second press
  waits for the same check), and the page reloads the list until it is newer than that start.
  Its `GITHUB_TOKEN` is a reference to the trigger's (`${{trigger.GITHUB_TOKEN}}`), so a new
  token goes into "trigger" only, followed by a redeploy of "button". The service sleeps when
  unused, so the first press after a while takes a few more seconds.
- `fetch.py` reads each channel's "UULF" playlist feed, which is the Videos tab without
  Shorts and live streams. It needs only the Python standard library.
- The page marks videos as **Nouveau** when this browser hadn't seen them at the start of
  the visit (a visit ends after 30 minutes away) and they're newer than the newest video
  already seen from that channel: when a video is deleted or turns into a Short, the feed
  brings an older one back, and that one isn't new. On a first visit, and for a newly added
  channel, the last 48 hours count. A video marked new always shows, even when it's older
  than the 30 days "Toutes" lists.

Run it locally:

```bash
python3 -m unittest -v
SSL_CERT_FILE=/etc/ssl/cert.pem python3 fetch.py   # the cert path is only needed with python.org's Python on macOS
python3 -m http.server 8790 --directory site
```
