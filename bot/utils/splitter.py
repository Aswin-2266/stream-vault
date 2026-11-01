import os
import subprocess
import math

TELEGRAM_MAX_BYTES = 1950 * 1024 * 1024  # 1.95 GB safe ceiling (under 2GB)

def get_file_size(file_path: str) -> int:
    return os.path.getsize(file_path)

def get_video_duration(file_path: str) -> float:
    """Extracts duration of video in seconds using ffprobe"""
    try:
        cmd = [
            "ffprobe",
            "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            file_path
        ]
        output = subprocess.check_output(cmd).decode().strip()
        return float(output)
    except Exception as e:
        print(f"[!] ffprobe duration extraction failed: {e}")
        return 0.0

def split_video_file(file_path: str) -> list[str]:
    """
    Splits video into parts under 1.95 GB using lossless ffmpeg stream copy (-c copy).
    Returns list of output file paths.
    """
    file_size = get_file_size(file_path)
    if file_size <= TELEGRAM_MAX_BYTES:
        return [file_path]

    duration = get_video_duration(file_path)
    num_parts = math.ceil(file_size / TELEGRAM_MAX_BYTES)
    if num_parts < 2 or duration <= 0:
        return [file_path]

    segment_time = duration / num_parts
    base_name, ext = os.path.splitext(file_path)
    output_pattern = f"{base_name}.part%02d{ext}"

    print(f"[+] File is {file_size / (1024*1024):.2f}MB (>1.95GB). Splitting into {num_parts} parts using ffmpeg stream copy...")

    cmd = [
        "ffmpeg",
        "-i", file_path,
        "-c", "copy",
        "-map", "0",
        "-f", "segment",
        "-segment_time", str(segment_time),
        "-reset_timestamps", "1",
        output_pattern
    ]

    try:
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        # Collect created parts
        directory = os.path.dirname(file_path) or "."
        base_filename = os.path.basename(base_name)
        parts = []
        for f in sorted(os.listdir(directory)):
            if f.startswith(base_filename + ".part") and f.endswith(ext):
                parts.append(os.path.join(directory, f))

        if parts:
            print(f"[+] Successfully split video into {len(parts)} parts.")
            return parts
    except Exception as e:
        print(f"[!] ffmpeg split failed: {e}. Falling back to original file.")

    return [file_path]
