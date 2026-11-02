import re
import datetime
import certifi
from motor.motor_asyncio import AsyncIOMotorClient
import config

class Database:
    def __init__(self):
        self._client = None
        self._db = None
        self._files = None

    def connect(self):
        if not config.MONGO_URI:
            print("[!] Database: MONGO_URI is not provided. Database functionality disabled.")
            return
        try:
            self._client = AsyncIOMotorClient(config.MONGO_URI, tlsCAFile=certifi.where())
            self._db = self._client[config.DATABASE_NAME]
            self._files = self._db["files"]
            self._queue = self._db["leech_queue"]
            print("[+] Database: Connected successfully to MongoDB Atlas.")
        except Exception as e:
            print(f"[!] Database Connection Error: {e}")

    async def save_file(self, file_info: dict) -> bool:
        """
        Saves or updates a file metadata record.
        Deduplicates based on unique_id.
        """
        if self._files is None:
            return False

        unique_id = file_info.get("unique_id")
        if not unique_id:
            return False

        file_info["updated_at"] = datetime.datetime.utcnow()
        await self._files.update_one(
            {"unique_id": unique_id},
            {"$set": file_info},
            upsert=True
        )
        return True

    async def search_files(self, query: str, limit: int = 15) -> list:
        """
        Search files using case-insensitive regex matching each word in the query.
        """
        if self._files is None:
            return []

        # Clean search query and split into word tokens
        tokens = query.strip().split()
        if not tokens:
            return []

        # Create regex pattern matching all tokens in any order
        # e.g. "Avatar 2" -> pattern matches items containing both Avatar and 2
        regex_pattern = "".join([f"(?=.*{re.escape(token)})" for token in tokens])
        search_filter = {"file_name": {"$regex": regex_pattern, "$options": "i"}}

        cursor = self._files.find(search_filter).limit(limit)
        results = []
        async for doc in cursor:
            # Convert ObjectId to string for easy serialization
            doc["_id"] = str(doc["_id"])
            results.append(doc)
        return results

    async def get_file_by_id(self, file_id: str) -> dict:
        """Fetch a single file document by its Telegram file_id or unique_id"""
        if self._files is None:
            return None
        return await self._files.find_one({"$or": [{"file_id": file_id}, {"unique_id": file_id}]})

    async def count_files(self) -> int:
        """Total number of indexed files"""
        if self._files is None:
            return 0
        return await self._files.count_documents({})

    async def add_to_queue(self, task: dict) -> str:
        """Add a download task to the cloud leech queue"""
        if self._queue is None:
            return ""
        task["status"] = task.get("status", "queued")
        task["created_at"] = datetime.datetime.utcnow()
        res = await self._queue.insert_one(task)
        return str(res.inserted_id)

    async def get_pending_queue_tasks(self, limit: int = 10) -> list:
        """Fetch pending tasks for the Google Colab or cloud worker"""
        if self._queue is None:
            return []
        cursor = self._queue.find({"status": "queued"}).sort("created_at", 1).limit(limit)
        tasks = []
        async for doc in cursor:
            doc["_id"] = str(doc["_id"])
            tasks.append(doc)
        return tasks

    async def update_queue_status(self, task_id: str, status: str, error: str = None) -> bool:
        """Update status of a queue task"""
        if self._queue is None:
            return False
        from bson import ObjectId
        update_doc = {
            "status": status,
            "updated_at": datetime.datetime.utcnow()
        }
        if error:
            update_doc["error"] = error
        await self._queue.update_one({"_id": ObjectId(task_id)}, {"$set": update_doc})
        return True

# Global singleton
db = Database()
