import os
import re
import time
import subprocess
import atexit

tunnel_process = None

def get_cloudflared_path() -> str:
    local_bin = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "bin", "cloudflared.exe")
    if os.path.exists(local_bin):
        return local_bin
    return "cloudflared"

def start_tunnel(port: int = 7860) -> str:
    """
    Starts an automated Cloudflare quick tunnel to give the local streaming server
    a public, secure HTTPS URL (accessible on phone, VLC, 1DM+, etc.)
    """
    global tunnel_process
    cf_path = get_cloudflared_path()
    log_file = "tunnel.log"

    print("[+] Starting Cloudflare Tunnel for public stream links...")
    try:
        tunnel_process = subprocess.Popen(
            [cf_path, "tunnel", "--url", f"http://localhost:{port}"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1
        )

        atexit.register(stop_tunnel)

        # Read stderr to extract the public URL
        url_pattern = re.compile(r"https://[a-zA-Z0-9\-]+\.trycloudflare\.com")
        start_time = time.time()
        
        while time.time() - start_time < 20:
            line = tunnel_process.stderr.readline()
            if not line:
                time.sleep(0.5)
                continue
            match = url_pattern.search(line)
            if match:
                tunnel_url = match.group(0)
                print(f"[+] Cloudflare Public Stream URL: {tunnel_url}")
                return tunnel_url

    except Exception as e:
        print(f"[!] Could not start Cloudflare tunnel: {e}")

    return None

def stop_tunnel():
    global tunnel_process
    if tunnel_process:
        try:
            tunnel_process.terminate()
            tunnel_process.wait(timeout=2)
        except Exception:
            pass
        tunnel_process = None
