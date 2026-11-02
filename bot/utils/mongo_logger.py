import os
import sys
import logging
import asyncio
import traceback
from datetime import datetime
from bot.utils.database import db

FALLBACK_LOG_DIR = "logs"
FALLBACK_LOG_FILE = os.path.join(FALLBACK_LOG_DIR, "fallback_errors.log")

class MongoDBHandler(logging.Handler):
    """
    Non-blocking, asynchronous logging handler that queues log records
    and writes them to MongoDB Atlas in a separate background worker.
    """
    def __init__(self, queue: asyncio.Queue, loop: asyncio.AbstractEventLoop = None):
        super().__init__()
        self.queue = queue
        self.loop = loop

    def emit(self, record: logging.LogRecord):
        # Format exception information if available
        tb_str = None
        if record.exc_info:
            tb_str = "".join(traceback.format_exception(*record.exc_info))
        elif record.exc_text:
            tb_str = record.exc_text

        log_data = {
            "level": record.levelname,
            "module": record.name,
            "message": record.getMessage(),
            "traceback": tb_str,
            "source": "main_bot",
            "time": datetime.utcnow()
        }

        try:
            self.queue.put_nowait(log_data)
        except Exception:
            pass  # Avoid raising exceptions inside logging handlers

async def _log_worker(queue: asyncio.Queue):
    """
    Background worker that consumes log items from the in-memory queue
    and persists them to MongoDB Atlas collections.
    """
    while True:
        try:
            log_item = await queue.get()
            level = log_item.get("level", "INFO").upper()
            module = log_item.get("module", "root")
            message = log_item.get("message", "")
            tb_str = log_item.get("traceback")
            source = log_item.get("source", "main_bot")

            # Route to dedicated error_logs or system_logs
            if level in ["WARNING", "ERROR", "CRITICAL"]:
                success = await db.log_error(
                    level=level,
                    module=module,
                    message=message,
                    traceback=tb_str,
                    source=source
                )
            else:
                success = await db.log_system(
                    level=level,
                    module=module,
                    message=message,
                    source=source
                )

            # If write failed or Mongo is disconnected, append to fallback file
            if not success and level in ["WARNING", "ERROR", "CRITICAL"]:
                _write_fallback(log_item)

            queue.task_done()
        except asyncio.CancelledError:
            break
        except Exception as e:
            # Catch all so the worker never dies
            try:
                _write_fallback({"level": "ERROR", "module": "MongoLogger", "message": f"Worker error: {e}"})
            except Exception:
                pass

def _write_fallback(log_item: dict):
    """Writes failed error logs to a local disk file as a safety fallback"""
    try:
        os.makedirs(FALLBACK_LOG_DIR, exist_ok=True)
        with open(FALLBACK_LOG_FILE, "a", encoding="utf-8") as f:
            t = log_item.get("time", datetime.utcnow()).strftime("%Y-%m-%d %H:%M:%S")
            lvl = log_item.get("level", "ERROR")
            mod = log_item.get("module", "unknown")
            msg = log_item.get("message", "")
            f.write(f"[{t}] [{lvl}] [{mod}] {msg}\n")
            if log_item.get("traceback"):
                f.write(f"{log_item['traceback']}\n")
    except Exception:
        pass

def setup_mongo_logging() -> asyncio.Task:
    """
    Hooks MongoDBHandler into the Python root logger and launches
    the background queue consumer task.
    """
    queue = asyncio.Queue(maxsize=1000)
    loop = asyncio.get_event_loop()
    mongo_handler = MongoDBHandler(queue, loop=loop)
    mongo_handler.setLevel(logging.INFO)

    root_logger = logging.getLogger()
    # Avoid attaching duplicate handlers
    if not any(isinstance(h, MongoDBHandler) for h in root_logger.handlers):
        root_logger.addHandler(mongo_handler)

    worker_task = asyncio.create_task(_log_worker(queue))
    return worker_task
