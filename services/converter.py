import os
import subprocess
import logging
import gc

def convert_for_ios(input_path: str) -> str:
    """
    Xotirani tejaydigan (RAM tejamkor) va iPhone uchun to'liq moslashtirilgan konvertatsiya.
    Maksimal ruxsat: 720p, 1 oqim (threads 1), ultrafast.
    """
    if not input_path or not os.path.exists(input_path):
        return input_path

    output_path = input_path.rsplit(".", 1)[0] + "_ios.mp4"

    cmd = [
        "ffmpeg", "-y", "-i", input_path,
        "-vf", "scale='min(720,iw)':-2",  # Agar video 1080p/4K bo'lsa, xotira to'lmasligi uchun 720p ga tushiradi
        "-c:v", "libx264",
        "-preset", "ultrafast",            # Xotirani eng kam sarflaydigan rejim
        "-crf", "26",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", "96k",
        "-threads", "1",                   # RAM ko'tarilib ketmasligi uchun 1 oqim
        "-movflags", "+faststart",
        output_path
    ]

    try:
        result = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=45)
        if result.returncode == 0 and os.path.exists(output_path) and os.path.getsize(output_path) > 0:
            if os.path.exists(input_path) and input_path != output_path:
                os.remove(input_path)
            gc.collect() # Xotirani darhol tozalash
            return output_path
    except Exception as e:
        logging.warning(f"iOS formatlashda xatolik: {e}")

    gc.collect()
    return input_path
