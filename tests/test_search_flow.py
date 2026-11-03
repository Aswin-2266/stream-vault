import unittest
from bot.handlers.search import SEARCH_CACHE, render_torrent_view, get_query_id

class TestSearchSelectionFlow(unittest.TestCase):
    def setUp(self):
        self.qid = get_query_id("Inception")
        SEARCH_CACHE[self.qid] = {
            "query": "Inception",
            "clean_title": "Inception",
            "suggested_title": None,
            "vault_results": [],
            "torrent_results": [
                {
                    "title": "Inception.2010.1080p.BluRay.x264",
                    "quality": "1080p",
                    "languages": "English",
                    "size": "2.2 GB",
                    "seeds": 150,
                    "seed_badge": "🌱 150 Seeds",
                    "hash": "abc123hash",
                    "magnet": "magnet:?xt=urn:btih:abc123hash"
                },
                {
                    "title": "Inception.2010.720p.BluRay.x264",
                    "quality": "720p",
                    "languages": "English",
                    "size": "1.1 GB",
                    "seeds": 80,
                    "seed_badge": "🌱 80 Seeds",
                    "hash": "def456hash",
                    "magnet": "magnet:?xt=urn:btih:def456hash"
                }
            ],
            "vault_page": 0,
            "torrent_page": 0
        }

    def test_render_torrent_view_has_selection_callbacks(self):
        text, markup = render_torrent_view(self.qid, page=0)
        self.assertIn("Inception", text)
        self.assertIsNotNone(markup)

        # Check button callback data starts with sel_tor_
        sel_callbacks = []
        for row in markup.inline_keyboard:
            for btn in row:
                if btn.callback_data and btn.callback_data.startswith("sel_tor_"):
                    sel_callbacks.append(btn.callback_data)

        self.assertEqual(len(sel_callbacks), 2)
        self.assertTrue(any("abc123hash" in c for c in sel_callbacks))
        self.assertTrue(any("def456hash" in c for c in sel_callbacks))

if __name__ == "__main__":
    unittest.main()
