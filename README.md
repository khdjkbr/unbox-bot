# Video download bot

For a local install, use Python 3.11+, FFmpeg and Node.js 22+. Install
`requirements.txt`, copy `.env.example` to `.env`, set `BOT_TOKEN`, then run
`python bot.py`. The Dockerfile includes FFmpeg and Node.js.
Run only one polling process per bot token.
The bot must be an administrator of `@unbox_uzb` for reliable subscription checks.

The Dockerfile health check requests `GET /` on the container's loopback
address using `PORT` (default `10000`). It checks that the bot process can
serve HTTP. Keep Coolify's dashboard health-check override disabled to use
the image check. Configure single-container replacement for the polling bot.

## Diagnostics

- Check hosting logs for `Media download/upload failed` and the traceback.
- Instagram can behave differently on hosting IPs. If logs require authentication,
  configure `YTDLP_COOKIES_FILE` with a private Netscape-format cookies file.
  Do not commit cookies or tokens. Cookies do not guarantee access to every post.
- `RAPIDAPI_KEY` is optional and requires access to the configured API. On failure,
  Instagram falls back to yt-dlp.
- Update yt-dlp when a platform changes its extractor requirements.
- YouTube prefers up to 720p and skips formats reported to exceed the 50 MiB
  upload budget. When the size is unavailable, the downloader checks the completed
  file. `yt-dlp[default]` installs the JavaScript challenge scripts used with Node.js.
- `YOINKU_API_KEY` optionally enables the existing YouTube fallback when direct
  download fails. Set it as a runtime secret if you use this service.
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
