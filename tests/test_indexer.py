import unittest
from unittest.mock import AsyncMock, MagicMock, patch
import config
from bot.handlers.indexer import auto_save_handler
from bot.utils.vm_leech import send_telegram_progress

class TestIndexerSaveOnce(unittest.IsolatedAsyncioTestCase):
    @patch("bot.handlers.indexer.is_authorized", return_value=True)
    @patch("bot.handlers.indexer.db")
    async def test_duplicate_file_not_copied_returns_same_link(self, mock_db, mock_auth):
        # Existing file in database
        mock_db.get_file_by_id = AsyncMock(return_value={
            "file_name": "Movie.2024.1080p.mkv",
            "file_size": 1500000000,
            "unique_id": "uniq_dup_123",
            "file_id": "vault_fid_existing"
        })
        mock_db.save_file = AsyncMock()

        # Mock incoming forwarded message
        mock_media = MagicMock()
        mock_media.file_name = "Movie.2024.1080p.mkv"
        mock_media.file_size = 1500000000
        mock_media.file_unique_id = "uniq_dup_123"
        mock_media.mime_type = "video/mp4"

        mock_msg = MagicMock()
        mock_msg.from_user.id = 1882765881
        mock_msg.video = mock_media
        mock_msg.document = None
        mock_msg.copy = AsyncMock()
        mock_msg.reply_text = AsyncMock()

        mock_client = MagicMock()

        await auto_save_handler(mock_client, mock_msg)

        # 1. Verify message.copy was NOT called (no duplicate copy in Vault channel)
        mock_msg.copy.assert_not_called()

        # 2. Verify reply contains existing link and "Already in Vault"
        mock_msg.reply_text.assert_called_once()
        reply_caption = mock_msg.reply_text.call_args[0][0]
        self.assertIn("Already in Vault!", reply_caption)
        self.assertIn("uniq_dup_123", reply_caption)

    @patch("bot.handlers.indexer.is_authorized", return_value=True)
    @patch("bot.handlers.indexer.db")
    async def test_new_file_copied_once_and_saved(self, mock_db, mock_auth):
        # File not yet in database
        mock_db.get_file_by_id = AsyncMock(return_value=None)
        mock_db.save_file = AsyncMock()

        mock_media = MagicMock()
        mock_media.file_name = "NewMovie.mp4"
        mock_media.file_size = 800000000
        mock_media.file_unique_id = "uniq_new_456"
        mock_media.mime_type = "video/mp4"

        mock_copied_media = MagicMock()
        mock_copied_media.file_id = "vault_new_fid_999"
        mock_copied = MagicMock()
        mock_copied.video = mock_copied_media
        mock_copied.document = None

        mock_status = MagicMock()
        mock_status.edit_text = AsyncMock()

        mock_msg = MagicMock()
        mock_msg.from_user.id = 1882765881
        mock_msg.chat.id = 1882765881
        mock_msg.caption = None
        mock_msg.video = mock_media
        mock_msg.document = None
        mock_msg.copy = AsyncMock(return_value=mock_copied)
        mock_msg.reply_text = AsyncMock(return_value=mock_status)

        mock_client = MagicMock()

        await auto_save_handler(mock_client, mock_msg)

        # 1. Verify message.copy was called exactly once to LOG_CHANNEL_ID
        mock_msg.copy.assert_called_once_with(chat_id=config.LOG_CHANNEL_ID)

        # 2. Verify file was saved in DB
        mock_db.save_file.assert_called_once()

        # 3. Verify status edited with new stream link
        mock_status.edit_text.assert_called_once()
        reply_caption = mock_status.edit_text.call_args[0][0]
        self.assertIn("Saved to Vault!", reply_caption)
        self.assertIn("uniq_new_456", reply_caption)

    @patch("bot.utils.vm_leech.requests.post")
    def test_send_telegram_progress_no_stream_button(self, mock_post):
        mock_res = MagicMock()
        mock_res.status_code = 200
        mock_res.text = "ok"
        mock_post.return_value = mock_res

        send_telegram_progress(
            bot_token="test_token",
            chat_id=123,
            message_id=456,
            title="Inception",
            size="2.2 GB",
            seeds="50",
            magnet="magnet:?xt=urn:btih:ABCDEF1234567890",
            pct=100,
            stream_url="http://140.245.193.224:7860/stream/uniq123"
        )

        mock_post.assert_called_once()
        payload = mock_post.call_args[1]["json"]
        buttons = payload.get("reply_markup", {}).get("inline_keyboard", [])

        # Ensure no URL stream button exists
        for row in buttons:
            for btn in row:
                self.assertNotIn("Stream", btn.get("text", ""))
                self.assertNotIn("url", btn)

        # Ensure Copy Magnet button is present
        self.assertTrue(any(btn.get("callback_data", "").startswith("copy_mag_") for row in buttons for btn in row))

if __name__ == "__main__":
    unittest.main()
