#!/usr/bin/env python3
"""Fetch the latest long videos (no Shorts, no lives) of every channel in channels.txt.

Writes two files:
  data/state.json   committed: channel info and video list, changes only when videos change
  site/videos.json  published: the same plus view counts and the time of the check

Long videos come from the channel's "UULF" playlist feed, which is the Videos tab
without Shorts and live streams. Only the Python standard library is used.
"""
from __future__ import annotations

import html
import json
import re
import time
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CHANNELS_FILE = ROOT / "channels.txt"
STATE_FILE = ROOT / "data" / "state.json"
SITE_FILE = ROOT / "site" / "videos.json"

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/130.0 Safari/537.36")
NS = {
    "a": "http://www.w3.org/2005/Atom",
    "yt": "http://www.youtube.com/xml/schemas/2015",
    "media": "http://search.yahoo.com/mrss/",
}
CHANNEL_ID = re.compile(r"UC[\w-]{22}")


def normalize(text: str) -> str | None:
    """Turn '@Handle', 'Handle', a channel URL or a UC… id into a lookup key."""
    text = text.strip()
    m = re.search(r"youtube\.com/channel/(UC[\w-]{22})", text)
    if m:
        return m.group(1)
    if CHANNEL_ID.fullmatch(text):
        return text
    m = re.search(r"youtube\.com/(@[\w.\-]+)", text)
    if m:
        return m.group(1).lower()
    if re.fullmatch(r"@?[\w.\-]+", text):
        return ("@" + text.lstrip("@")).lower()
    return None


def read_channels(path: Path = CHANNELS_FILE) -> list[str]:
    """One channel per line; '#' starts a comment."""
    keys: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.split("#", 1)[0].strip()
        key = normalize(line) if line else None
        if line and not key:
            print(f"::warning::channels.txt: can't read {line!r}")
        if key and key not in keys:
            keys.append(key)
    return keys


def fetch(url: str, tries: int = 3) -> bytes:
    """GET with retries: YouTube feeds sometimes answer 404 or 5xx for a few seconds."""
    error: Exception = RuntimeError("no attempt made")
    for attempt in range(tries):
        if attempt:
            time.sleep(2 * attempt)
        req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "fr-FR,fr;q=0.9"})
        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                return resp.read()
        except urllib.error.HTTPError as e:
            error = e
            if e.code not in (404, 429, 500, 502, 503, 504):
                break
        except (urllib.error.URLError, TimeoutError) as e:
            error = e
    raise error


def resolve(key: str) -> dict:
    """Read a channel's id, handle, name and avatar from its YouTube page."""
    path = f"channel/{key}" if CHANNEL_ID.fullmatch(key) else key
    page = fetch(f"https://www.youtube.com/{path}").decode("utf-8", "replace")
    m = re.search(r'<link rel="canonical" href="https://www\.youtube\.com/channel/(UC[\w-]{22})"', page)
    if not m:
        raise ValueError("no channel id on the page")

    def og(prop: str) -> str:
        mm = re.search(rf'<meta property="og:{prop}" content="([^"]*)"', page)
        return html.unescape(mm.group(1)) if mm else ""

    handle = re.search(r'"vanityChannelUrl":"https?://www\.youtube\.com/(@[^"]+)"', page)
    return {
        "id": m.group(1),
        "handle": handle.group(1) if handle else (key if key.startswith("@") else ""),
        "name": og("title") or key,
        "avatar": re.sub(r"=s\d+-", "=s176-", og("image")),
    }


def parse_feed(xml_bytes: bytes) -> tuple[str, list[dict]]:
    """Return the feed's author name and its videos, newest first."""
    root = ET.fromstring(xml_bytes)
    author = root.findtext("a:author/a:name", default="", namespaces=NS)
    videos = []
    for entry in root.findall("a:entry", NS):
        vid = entry.findtext("yt:videoId", namespaces=NS)
        if not vid:
            continue
        stats = entry.find("media:group/media:community/media:statistics", NS)
        videos.append({
            "id": vid,
            "title": entry.findtext("a:title", default="", namespaces=NS),
            "published": entry.findtext("a:published", default="", namespaces=NS),
            "views": int(stats.get("views", 0)) if stats is not None else None,
        })
    videos.sort(key=lambda v: v["published"], reverse=True)
    return author, videos


def get_feed(channel_id: str) -> tuple[str, list[dict]]:
    playlist = "UULF" + channel_id[2:]
    return parse_feed(fetch(f"https://www.youtube.com/feeds/videos.xml?playlist_id={playlist}"))


def check(keys: list[str], old: dict, resolve_fn=resolve, feed_fn=get_feed) -> tuple[dict, dict]:
    """Build the new state and the published data from channels.txt keys and the previous state."""
    known = old.get("channels", {})
    infos: dict[str, dict] = {}
    for key in keys:
        if key in known:
            infos[key] = known[key]
            continue
        try:
            infos[key] = resolve_fn(key)
            print(f"found {key}: {infos[key]['name']} ({infos[key]['id']})")
        except Exception as e:  # noqa: BLE001 - any failure means "not found this run"
            print(f"::warning::could not find channel {key}: {e}")

    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = {key: pool.submit(feed_fn, info["id"]) for key, info in infos.items()}

    state: dict = {"channels": {}, "videos": {}}
    channels: list[dict] = []
    videos: list[dict] = []
    for key in keys:
        info = infos.get(key)
        if info is None:
            channels.append({"key": key, "id": None, "handle": key if key.startswith("@") else "",
                             "name": key, "avatar": "", "ok": False, "error": "not_found"})
            continue
        cid = info["id"]
        try:
            author, vids = futures[key].result()
            info = {**info, "name": author or info["name"]}
            status = {"ok": True}
        except Exception as e:  # noqa: BLE001 - keep the last good list instead
            vids = old.get("videos", {}).get(cid, [])
            status = {"ok": False, "error": "feed_unavailable"}
            print(f"::warning::feed unavailable for {info['name']} ({cid}): {e}")
        state["channels"][key] = info
        state["videos"][cid] = [{k: v[k] for k in ("id", "title", "published")} for v in vids]
        channels.append({"key": key, **info, **status})
        videos += [{**v, "ch": cid} for v in vids]

    videos.sort(key=lambda v: v["published"], reverse=True)
    checked_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    return state, {"checked_at": checked_at, "channels": channels, "videos": videos}


def main() -> int:
    old = json.loads(STATE_FILE.read_text(encoding="utf-8")) if STATE_FILE.exists() else {}
    state, site = check(read_channels(), old)

    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    SITE_FILE.parent.mkdir(parents=True, exist_ok=True)
    SITE_FILE.write_text(json.dumps(site, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")

    for c in site["channels"]:
        latest = next((v for v in site["videos"] if v["ch"] == c["id"]), None)
        flag = "ok " if c["ok"] else "ERR"
        print(f"{flag} {c['name']:<16} {latest['published'][:16] if latest else '-':<16} "
              f"{latest['title'][:60] if latest else c.get('error', '')}")
    print(f"{len(site['videos'])} videos from {len(site['channels'])} channels, checked {site['checked_at']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
