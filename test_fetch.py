"""Run with: python3 -m unittest -v"""
import unittest

from fetch import check, normalize, parse_feed

FEED = b"""<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns:yt="http://www.youtube.com/xml/schemas/2015" xmlns:media="http://search.yahoo.com/mrss/"
      xmlns="http://www.w3.org/2005/Atom">
 <author><name>Amixem</name></author>
 <entry>
  <yt:videoId>older0000001</yt:videoId>
  <title>DEVINE QUI TU ES #4 ft. CYPRIEN</title>
  <published>2026-10-25T16:25:00+00:00</published>
 </entry>
 <entry>
  <yt:videoId>4X440MciNX8</yt:videoId>
  <title>J&#8217;AI ACHET\xc3\x89 DES JOUETS G\xc3\x89ANTS !</title>
  <published>2026-11-01T16:25:00+00:00</published>
  <media:group><media:community><media:statistics views="2965051"/></media:community></media:group>
 </entry>
</feed>"""


class NormalizeTest(unittest.TestCase):
    def test_handles_urls_and_ids(self):
        cid = "UCWeg2Pkate69NFdBeuRFTAw"
        self.assertEqual(normalize("@Squeezie"), "@squeezie")
        self.assertEqual(normalize("Squeezie"), "@squeezie")
        self.assertEqual(normalize("https://www.youtube.com/@MaximeBiaggi/videos"), "@maximebiaggi")
        self.assertEqual(normalize(f"https://www.youtube.com/channel/{cid}"), cid)
        self.assertEqual(normalize(cid), cid)
        self.assertIsNone(normalize("pas une chaîne !"))


class ParseFeedTest(unittest.TestCase):
    def test_reads_entries_newest_first(self):
        author, videos = parse_feed(FEED)
        self.assertEqual(author, "Amixem")
        self.assertEqual([v["id"] for v in videos], ["4X440MciNX8", "older0000001"])
        self.assertEqual(videos[0]["title"], "J’AI ACHETÉ DES JOUETS GÉANTS !")
        self.assertEqual(videos[0]["views"], 2965051)
        self.assertIsNone(videos[1]["views"])


class CheckTest(unittest.TestCase):
    def test_merges_channels_and_keeps_last_list_when_a_feed_fails(self):
        old = {
            "channels": {
                "@amixem": {"id": "UCa", "handle": "@Amixem", "name": "Amixem", "avatar": ""},
                "@djilsi": {"id": "UCd", "handle": "@Djilsi", "name": "Djilsi", "avatar": ""},
            },
            "videos": {"UCd": [{"id": "d1", "title": "Ancienne", "published": "2026-10-24T08:59:00+00:00"}]},
        }

        def resolve(key):
            if key == "@squeezie":
                return {"id": "UCs", "handle": "@Squeezie", "name": "SQUEEZIE", "avatar": "a.jpg"}
            raise ValueError("404")

        def feed(cid):
            if cid == "UCd":
                raise OSError("timeout")
            return {"UCa": ("Amixem", [{"id": "a1", "title": "A", "published": "2026-11-01T16:25:00+00:00", "views": 5}]),
                    "UCs": ("SQUEEZIE", [{"id": "s1", "title": "S", "published": "2026-10-04T16:45:00+00:00", "views": 9}])}[cid]

        state, site = check(["@squeezie", "@djilsi", "@nobody", "@amixem"], old, resolve, feed)

        self.assertEqual([c["key"] for c in site["channels"]], ["@squeezie", "@djilsi", "@nobody", "@amixem"])
        status = {c["key"]: (c["ok"], c.get("error")) for c in site["channels"]}
        self.assertEqual(status["@djilsi"], (False, "feed_unavailable"))
        self.assertEqual(status["@nobody"], (False, "not_found"))
        self.assertEqual(status["@squeezie"], (True, None))
        self.assertEqual([v["id"] for v in site["videos"]], ["a1", "d1", "s1"])
        self.assertEqual(site["videos"][0]["ch"], "UCa")
        # The committed state holds no view counts, so it only changes when videos change.
        self.assertEqual(state["videos"]["UCa"], [{"id": "a1", "title": "A", "published": "2026-11-01T16:25:00+00:00"}])
        self.assertEqual(state["videos"]["UCd"], old["videos"]["UCd"])
        self.assertIn("@squeezie", state["channels"])
        self.assertNotIn("@nobody", state["channels"])


if __name__ == "__main__":
    unittest.main()
