import os
import subprocess
import logging
import gc

def convert_for_ios(input_path: str) -> str:
    """
    iPhone (iOS) da qotib qolishni (rasm to'xtab, ovoz ketishini) 
    100% bartaraf etuvchi barqaror H.264 + AAC + CFR (30fps) konvertatsiya.
    """
    if not input_path or not os.path.exists(input_path):
        return input_path

    output_path = input_path.rsplit(".", 1)[0] + "_ios.mp4"

    cmd = [
        "ffmpeg", "-y", "-i", input_path,
        "-vf", "scale=w='min(720,trunc(iw/2)*2)':h='trunc(ih/2)*2':force_original_aspect_ratio=decrease,pad='ceil(iw/2)*2':'ceil(ih/2)*2'",
        "-c:v", "libx264",
        "-profile:v", "main",
        "-level", "3.1",
        "-preset", "veryfast",
        "-crf", "24",
        "-r", "30",                         # Qotib qolmasligi uchun kadrlar chastotasini 30 fps ga tekislash
        "-g", "60",                         # Har 2 soniyada tayanch kadr (GOP keyframe)
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", "128k",
        "-ar", "44100",
        "-threads", "1",                    # RAM to'lib ketmasligi uchun 1 oqim
        "-movflags", "+faststart",
        output_path
    ]

    try:
        result = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=60)
        if result.returncode == 0 and os.path.exists(output_path) and os.path.getsize(output_path) > 0:
            if os.path.exists(input_path) and input_path != output_path:
                os.remove(input_path)
            gc.collect()
            return output_path
    except Exception as e:
        logging.warning(f"iOS konvertatsiyada xatolik: {e}")

    gc.collect()
    return input_path
