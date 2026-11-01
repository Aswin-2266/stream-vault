import re
from aiohttp import web
import config
from bot.utils.database import db

routes = web.RouteTableDef()
bot_instance = None

def set_bot_instance(bot):
    global bot_instance
    bot_instance = bot

@routes.get("/")
async def root_handler(request):
    total = await db.count_files()
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>StreamVault Gateway</title>
        <style>
            body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #0f172a; color: #f8fafc; display: flex; align-items: center; justify-content: center; height: 100vh; margin: 0; }}
            .card {{ background: #1e293b; padding: 2rem 3rem; border-radius: 12px; box-shadow: 0 10px 25px rgba(0,0,0,0.5); text-align: center; border: 1px solid #334155; }}
            h1 {{ margin-bottom: 0.5rem; color: #38bdf8; }}
            p {{ color: #94a3b8; font-size: 1.1rem; }}
            .badge {{ display: inline-block; padding: 0.25rem 0.75rem; border-radius: 9999px; background: #0284c7; color: white; font-weight: 600; font-size: 0.875rem; }}
        </style>
    </head>
    <body>
        <div class="card">
            <h1>⚡ StreamVault Gateway</h1>
            <p>Cloud Media Relay & Range-Request Streamer</p>
            <div class="badge">Status: Online | Indexed Files: {total}</div>
        </div>
    </body>
    </html>
    """
    return web.Response(text=html, content_type="text/html")

@routes.get("/stream/{file_id}")
async def stream_handler(request):
    """
    Streams a video chunk directly from Telegram using HTTP Range Requests.
    Enables instant seeking in VLC, MPV, and web browsers.
    """
    file_id = request.match_info.get("file_id")
    file_doc = await db.get_file_by_id(file_id)

    if not file_doc:
        return web.Response(text="File not found in database.", status=404)

    file_size = file_doc.get("file_size", 0)
    file_name = file_doc.get("file_name", "video.mp4")
    mime_type = file_doc.get("mime_type", "video/mp4")
    tg_file_id = file_doc.get("file_id", file_id)

    range_header = request.headers.get("Range")
    
    if not range_header:
        # Full content response header
        headers = {
            "Content-Type": mime_type,
            "Content-Length": str(file_size),
            "Content-Disposition": f'inline; filename="{file_name}"',
            "Accept-Ranges": "bytes"
        }
        response = web.StreamResponse(status=200, headers=headers)
        await response.prepare(request)
        if bot_instance:
            async for chunk in bot_instance.stream_media(tg_file_id):
                await response.write(chunk)
        return response

    # Parse Range: bytes=start-end
    range_match = re.match(r"bytes=(\d+)-(\d*)", range_header)
    if not range_match:
        return web.Response(status=416, text="Invalid Range header")

    start_byte = int(range_match.group(1))
    end_byte = int(range_match.group(2)) if range_match.group(2) else file_size - 1
    content_length = (end_byte - start_byte) + 1

    headers = {
        "Content-Type": mime_type,
        "Content-Range": f"bytes {start_byte}-{end_byte}/{file_size}",
        "Content-Length": str(content_length),
        "Content-Disposition": f'inline; filename="{file_name}"',
        "Accept-Ranges": "bytes"
    }

    response = web.StreamResponse(status=206, headers=headers)
    await response.prepare(request)

    if bot_instance:
        # Stream chunks starting from requested offset
        async for chunk in bot_instance.stream_media(tg_file_id, offset=start_byte, limit=content_length):
            await response.write(chunk)

    return response

async def start_web_server():
    """Initializes and runs the streaming HTTP web server"""
    app = web.Application()
    app.add_routes(routes)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, config.HOST, config.PORT)
    await site.start()
    print(f"[+] Web Streamer: Online on {config.STREAM_URL} (Port {config.PORT})")
    return runner
