import unittest
from bot.handlers.search import (
    SEARCH_CACHE,
    render_torrent_view,
    render_channel_view,
    render_vault_view,
    get_query_id
)

class TestSearchSelectionFlow(unittest.TestCase):
    def setUp(self):
        self.qid = get_query_id("Inception")
        SEARCH_CACHE[self.qid] = {
            "query": "Inception",
            "clean_title": "Inception",
            "suggested_title": None,
            "vault_results": [
                {
                    "file_name": "Inception.2010.1080p.Vault.mp4",
                    "file_size": 2000000000,
                    "file_id": "vlt_fid_1",
                    "unique_id": "vlt_uniq_1"
                }
            ],
            "channel_results": [
                {
                    "file_name": "Inception (2010) [1080p - Telugu + Tamil + Hindi].mkv",
                    "quality": "1080p",
                    "languages": "Telugu + Tamil + Hindi",
                    "size": "2.10 GB",
                    "size_bytes": 2254857830,
                    "source_chat_title": "TamilBlasters HD",
                    "source_chat_id": -1001234567,
                    "message_id": 999,
                    "harvest_id": "hid_inc_1080"
                }
            ],
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
            "channel_page": 0,
            "torrent_page": 0
        }

    def test_render_torrent_view_has_selection_callbacks(self):
        text, markup = render_torrent_view(self.qid, page=0)
        self.assertIn("Inception", text)
        self.assertIsNotNone(markup)

        sel_callbacks = []
        for row in markup.inline_keyboard:
            for btn in row:
                if btn.callback_data and btn.callback_data.startswith("sel_tor_"):
                    sel_callbacks.append(btn.callback_data)

        self.assertEqual(len(sel_callbacks), 2)
        self.assertTrue(any("abc123hash" in c for c in sel_callbacks))
        self.assertTrue(any("def456hash" in c for c in sel_callbacks))

    def test_tab_switchers_present_across_views(self):
        # Vault view should switch cleanly to Torrents
        _, v_markup = render_vault_view(self.qid, page=0)
        v_callbacks = [b.callback_data for r in v_markup.inline_keyboard for b in r]
        self.assertTrue(any("sw_tor_" in c for c in v_callbacks))
        self.assertFalse(any("sw_chn_" in c for c in v_callbacks))

        # Torrent view should switch cleanly to Vault
        _, t_markup = render_torrent_view(self.qid, page=0)
        t_callbacks = [b.callback_data for r in t_markup.inline_keyboard for b in r]
        self.assertTrue(any("sw_vlt_" in c for c in t_callbacks))
        self.assertFalse(any("sw_chn_" in c for c in t_callbacks))

if __name__ == "__main__":
    unittest.main()
