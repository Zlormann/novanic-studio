"""Tests hors réseau pour la synchronisation NovaNic."""
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "sync_soundcloud.py"
spec = importlib.util.spec_from_file_location("novanic_sync", SCRIPT)
sync = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sync)

def track(i, title="Chanson d'essai"):
    return {"id": str(i), "title": title, "url": "https://soundcloud.com/novanic/chanson-" + str(i),
            "cover": "", "description": ""}

class SyncTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.patchers = [
            patch.object(sync, "ROOT", self.root),
            patch.object(sync, "BASE", self.root / "chansons"),
            patch.object(sync, "ANNOUNCES", self.root / "annonces"),
            patch.object(sync, "blogger_token", return_value=None),
        ]
        for p in self.patchers:
            p.start()

    def tearDown(self):
        for p in reversed(self.patchers):
            p.stop()
        self.temp.cleanup()

    def state(self):
        return json.loads((self.root / "chansons" / "state.json").read_text())

    def test_initial_baseline_then_new_song(self):
        with patch.object(sync, "get_tracks", return_value=[track(1)]):
            sync.main()
        self.assertTrue(self.state()["tracks"]["1"]["baseline"])
        self.assertTrue(self.state()["tracks"]["1"]["blogger_done"])
        self.assertFalse((self.root / "annonces" / "1.md").exists())
        with patch.object(sync, "get_tracks", return_value=[track(1), track(2, "Ma nouvelle chanson")]):
            sync.main()
        s = self.state()
        self.assertFalse(s["tracks"]["2"]["baseline"])
        self.assertFalse(s["tracks"]["2"]["blogger_done"])
        self.assertEqual(s["tracks"]["2"]["blogger_status"], "en attente")
        self.assertTrue((self.root / "annonces" / "2.md").exists())
        self.assertIn("Ma nouvelle chanson", (self.root / "chansons" / "index.html").read_text())
        self.assertTrue((self.root / "journal" / "index.html").exists())
        with patch.object(sync, "get_tracks", return_value=[track(1), track(2, "Ma nouvelle chanson")]):
            sync.main()
        events = json.loads((self.root / "journal" / "events.json").read_text())
        self.assertEqual(sum(e["type"] == "nouvelle chanson" for e in events), 1)

    def test_escapes_titles_and_safe_urls(self):
        self.assertIn("&lt;script&gt;", sync.article(track(3, "<script>")))
        self.assertEqual(sync.safe_url("javascript:alert(1)"), "")
        self.assertEqual(sync.safe_url("https://soundcloud.com.evil.test/x", {"soundcloud.com"}), "")
        self.assertEqual(sync.slug_title("https://soundcloud.com/novanic/mon-beau-morceau"), "Mon Beau Morceau")

    def test_blogger_existing_post_prevents_duplicate(self):
        t = track(5)
        old = {"id": "abc", "content": "<!-- " + sync.marker(t) + " -->"}
        calls = []
        def fake(url, headers=None, data=None, method=None):
            calls.append((url, data))
            if "status=live" in url:
                return {"items": [old]}
            return {"items": []}
        with patch.object(sync, "request_json", side_effect=fake):
            result, existed = sync.post_blogger(t, "fake-token", "123")
        self.assertTrue(existed)
        self.assertEqual(result["id"], "abc")
        self.assertTrue(all(data is None for _, data in calls))

    def test_failed_soundcloud_keeps_state(self):
        with patch.object(sync, "get_tracks", return_value=[track(1)]):
            sync.main()
        original = (self.root / "chansons" / "state.json").read_bytes()
        with patch.object(sync, "get_tracks", side_effect=RuntimeError("offline")):
            with self.assertRaises(RuntimeError):
                sync.main()
        self.assertEqual((self.root / "chansons" / "state.json").read_bytes(), original)

    def test_existing_generic_title_is_repaired_without_republishing(self):
        (self.root / "chansons").mkdir()
        (self.root / "chansons" / "state.json").write_text(json.dumps({"version":1,"tracks":{
            "1":{"id":"1","title":"Nouvelle chanson NovaNic","url":track(1)["url"],
                 "blogger_done":True,"baseline":True}}}))
        with patch.object(sync, "get_tracks", return_value=[track(1,"Chanson corrigée")]):
            sync.main()
        self.assertEqual(self.state()["tracks"]["1"]["title"], "Chanson corrigée")
        self.assertTrue(self.state()["tracks"]["1"]["blogger_done"])

if __name__ == "__main__":
    unittest.main()
