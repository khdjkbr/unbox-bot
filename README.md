# Video download bot

Python 3.11+ and FFmpeg must be available. Install `requirements.txt`, copy
`.env.example` to `.env`, set `BOT_TOKEN`, then run `python bot.py`.
Docker includes FFmpeg. Run only one polling process per bot token.
The bot must be an administrator of `@unbox_uzb` for reliable subscription checks.

## Diagnostics

- Check hosting logs for `Media download/upload failed` and the traceback.
- Instagram can behave differently on hosting IPs. If logs require authentication,
  configure `YTDLP_COOKIES_FILE` with a private Netscape-format cookies file.
  Do not commit cookies or tokens. Cookies do not guarantee access to every post.
- `RAPIDAPI_KEY` is optional and requires access to the configured API. On failure,
  Instagram falls back to yt-dlp.
- Update yt-dlp when a platform changes its extractor requirements.
- YouTube now uses the download pipeline; platform authentication/JavaScript
  requirements can still apply. Only the first media item is downloaded.
- Store `downloads/bot_database.db` on persistent storage to preserve statistics.
- Self-pinging cannot guarantee continuous operation on hosting that suspends apps.

Run regression checks with `python -m unittest discover -s tests -v`.

## Verification on 2026-09-06

The supplied Instagram Reel `DcbOyxnir5M` downloaded locally as a 567251-byte MP4
with yt-dlp 2026.8.19, with both the original and revised Instagram downloader.
This does not reproduce the hosting failure. Hosting logs are needed to distinguish
IP restrictions, dependency versions, subscription checks and Telegram upload errors.
Telegram delivery and FFmpeg conversion were not tested end-to-end locally because
no bot token or FFmpeg executable was available.
