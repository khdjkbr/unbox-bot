import os
import subprocess
import logging

def convert_for_ios(input_path: str) -> str:
    """
    Videoni barcha iPhone (iOS) qurilmalarida qotmasdan va bir zumda 
    ochilishi uchun H.264 + AAC + yuv420p + faststart formatiga keltiradi.
    """
    if not input_path or not os.path.exists(input_path):
        return input_path

    output_path = input_path.rsplit(".", 1)[0] + "_ios.mp4"

    cmd = [
        "ffmpeg", "-y", "-i", input_path,
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-crf", "23",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", "128k",
        "-movflags", "+faststart",
        output_path
    ]

    try:
        result = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=60)
        if result.returncode == 0 and os.path.exists(output_path) and os.path.getsize(output_path) > 0:
            if os.path.exists(input_path) and input_path != output_path:
                os.remove(input_path)
            return output_path
    except Exception as e:
        logging.warning(f"iOS formatlashda xatolik: {e}")

    return input_path
