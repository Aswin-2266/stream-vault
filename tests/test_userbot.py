import unittest
from unittest.mock import MagicMock
from bot.utils.userbot import extract_media_info, format_size, UserbotHarvester

class TestUserbotHarvester(unittest.TestCase):
    def test_format_size(self):
        self.assertEqual(format_size(1024), "1.00 KB")
        self.assertEqual(format_size(1024 * 1024 * 500), "500.00 MB")
        self.assertEqual(format_size(1024 * 1024 * 1024 * 2), "2.00 GB")

    def test_extract_media_info_from_video(self):
        mock_msg = MagicMock()
        mock_msg.id = 123
        mock_msg.chat.id = -1009876543
        mock_msg.chat.title = "TamilBlasters Movies"
        mock_msg.caption = "The Shawshank Redemption 1994 1080p Telugu + Tamil + Hindi"
        mock_msg.video = MagicMock()
        mock_msg.video.file_name = "Shawshank.Redemption.1994.1080p.mkv"
        mock_msg.video.file_size = 1500 * 1024 * 1024  # 1.5 GB
        mock_msg.document = None

        info = extract_media_info(mock_msg)
        self.assertIsNotNone(info)
        self.assertEqual(info["file_name"], "Shawshank.Redemption.1994.1080p.mkv")
        self.assertEqual(info["quality"], "1080p")
        self.assertIn("Telugu", info["languages"])
        self.assertIn("Tamil", info["languages"])
        self.assertIn("Hindi", info["languages"])
        self.assertEqual(info["source_chat_id"], -1009876543)
        self.assertEqual(info["message_id"], 123)

    def test_extract_media_info_ignores_small_clips(self):
        mock_msg = MagicMock()
        mock_msg.id = 456
        mock_msg.video = MagicMock()
        mock_msg.video.file_name = "sample.mp4"
        mock_msg.video.file_size = 5 * 1024 * 1024  # 5 MB sample clip
        mock_msg.document = None

        info = extract_media_info(mock_msg)
        self.assertIsNone(info)

    def test_extract_media_info_ignores_non_video_documents(self):
        mock_msg = MagicMock()
        mock_msg.id = 789
        mock_msg.video = None
        mock_msg.document = MagicMock()
        mock_msg.document.file_name = "subtitles.srt"
        mock_msg.document.mime_type = "text/plain"
        mock_msg.document.file_size = 50 * 1024 * 1024

        info = extract_media_info(mock_msg)
        self.assertIsNone(info)

    def test_userbot_disabled_when_no_session(self):
        harvester = UserbotHarvester()
        self.assertFalse(harvester.is_available())

if __name__ == "__main__":
    unittest.main()
