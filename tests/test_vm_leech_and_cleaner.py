import os
import time
import shutil
import unittest
import config
from bot.utils.cleaner import get_disk_usage, clean_storage
from bot.utils.vm_leech import make_progress_bar, find_all_video_files, vm_leech_manager

class TestVMLeechAndCleaner(unittest.TestCase):
    def setUp(self):
        self.test_dir = "test_downloads_temp"
        os.makedirs(self.test_dir, exist_ok=True)
        self.original_download_dir = config.DOWNLOAD_DIR
        self.original_retention = config.STORAGE_RETENTION_DAYS
        config.DOWNLOAD_DIR = self.test_dir

    def tearDown(self):
        config.DOWNLOAD_DIR = self.original_download_dir
        config.STORAGE_RETENTION_DAYS = self.original_retention
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def test_progress_bar(self):
        bar_0 = make_progress_bar(0)
        self.assertEqual(bar_0, "░" * 14)
        bar_50 = make_progress_bar(50)
        self.assertEqual(bar_50, "█" * 7 + "░" * 7)
        bar_100 = make_progress_bar(100)
        self.assertEqual(bar_100, "█" * 14)

    def test_disk_usage(self):
        usage = get_disk_usage(".")
        self.assertIn("total_gb", usage)
        self.assertIn("percent_used", usage)
        self.assertGreater(usage["total_gb"], 0)

    def test_cleaner_retention(self):
        # Create an 'old' file (> 3 days old)
        old_file = os.path.join(self.test_dir, "old_movie.mp4")
        with open(old_file, "wb") as f:
            f.write(b"0" * 1024 * 100) # 100 KB
        # Set mtime to 4 days ago
        four_days_ago = time.time() - (4 * 86400)
        os.utime(old_file, (four_days_ago, four_days_ago))

        # Create a fresh file (1 hour ago)
        fresh_file = os.path.join(self.test_dir, "fresh_movie.mp4")
        with open(fresh_file, "wb") as f:
            f.write(b"1" * 1024 * 100)

        config.STORAGE_RETENTION_DAYS = 3
        res = clean_storage()

        self.assertEqual(res["deleted_files"], 1)
        self.assertFalse(os.path.exists(old_file), "Old file should have been purged")
        self.assertTrue(os.path.exists(fresh_file), "Fresh file should be retained")

    def test_find_all_video_files(self):
        # Create sample file (<25MB) and main movie (>25MB)
        sample = os.path.join(self.test_dir, "sample.mkv")
        movie = os.path.join(self.test_dir, "movie.1080p.mkv")
        with open(sample, "wb") as f:
            f.write(b"0" * 1024 * 1024) # 1 MB
        with open(movie, "wb") as f:
            f.seek(26 * 1024 * 1024) # 26 MB
            f.write(b"\0")

        videos = find_all_video_files(self.test_dir)
        self.assertEqual(len(videos), 1)
        self.assertEqual(os.path.basename(videos[0]), "movie.1080p.mkv")

    def test_vm_leech_manager_queue(self):
        test_task = {
            "task_id": "test_hash_123",
            "title": "Test Movie",
            "magnet": "magnet:?xt=urn:btih:test",
            "size": "1.5 GB",
            "seeds": 10,
            "chat_id": 12345,
            "message_id": 67890
        }
        info = vm_leech_manager.enqueue(test_task)
        self.assertIn("status", info)
        self.assertIn("Slot", info["status"])

if __name__ == "__main__":
    unittest.main()
