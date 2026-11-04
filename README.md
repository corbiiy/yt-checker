# Le Programme

The latest long videos (no Shorts, no lives) from a short list of YouTube channels,
on one page: https://corbiiy.github.io/yt-checker/

- `channels.txt` lists the channels, one per line (`@handle`, a channel URL or a `UC…` id).
  Edit it on GitHub to add or remove one; the page updates a minute or two after the commit.
- `.github/workflows/check.yml` runs `fetch.py` every 30 minutes from 15:00 to midnight,
  Paris time (`CHECK_FROM` in `site/index.html` must match), commits `data/state.json`
  when the video list changes, and deploys `site/` to GitHub Pages.
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
