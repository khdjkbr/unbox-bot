import os
import subprocess
import logging
import gc

def convert_for_ios(input_path: str) -> str:
    """
    Asl proporsiyani (9:16 vertikal, 16:9 gorizontal, 1:1 kvadrat) 100% buzmasdan saqlaydi
    va iPhone (iOS) hamda barcha smartfonlarda muammosiz ijro etilishini ta'minlaydi.
    """
    if not input_path or not os.path.exists(input_path):
        return input_path

    output_path = input_path.rsplit(".", 1)[0] + "_ios.mp4"

    cmd = [
        "ffmpeg", "-y", "-i", input_path,
        "-vf", "scale='trunc(min(720,iw)/2)*2':-2",  # Asl proporsiyani saqlaydi, 1:1 ga o'zgartirmaydi
        "-c:v", "libx264",
        "-profile:v", "main",
        "-level", "3.1",
        "-preset", "veryfast",
        "-crf", "24",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", "128k",
        "-threads", "1",
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
