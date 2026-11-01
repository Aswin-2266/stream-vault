import re
import datetime
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
            self._client = AsyncIOMotorClient(config.MONGO_URI)
            self._db = self._client[config.DATABASE_NAME]
            self._files = self._db["files"]
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

# Global singleton
db = Database()
