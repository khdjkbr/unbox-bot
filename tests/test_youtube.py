import unittest
from unittest.mock import AsyncMock, patch
from services import youtube
from services.downloader import DEFAULT_FORMAT, MAX_MEDIA_BYTES
from yt_dlp import YoutubeDL

class CascadeTests(unittest.IsolatedAsyncioTestCase):
    async def test_success_does_not_spend_api_quota(self):
        with (
            patch.object(youtube, 'download_media', AsyncMock(return_value='video.mp4')) as direct,
            patch.object(youtube.os.path, 'getsize', return_value=1000),
            patch.object(youtube, '_yoinku', AsyncMock()) as fallback,
        ):
            self.assertEqual(await youtube.download_youtube('url'), 'video.mp4')
            direct.assert_awaited_once_with('url', format_selector=youtube.YOUTUBE_FORMAT)
            fallback.assert_not_awaited()

    async def test_failure_uses_configured_fallback(self):
        with patch.object(youtube, 'download_media', AsyncMock(side_effect=RuntimeError('403'))), patch.object(youtube, '_yoinku', AsyncMock(return_value='fallback.mp4')) as fallback, patch.dict('os.environ', {'YOINKU_API_KEY': 'test'}):
            self.assertEqual(await youtube.download_youtube('url'), 'fallback.mp4')
            fallback.assert_awaited_once_with('url', 'test')

    def test_video_without_audio_is_rejected(self):
        with self.assertRaises(RuntimeError):
            youtube._format({'data': {'formats': [{'container': 'mp4', 'height': 720, 'hasVideo': True, 'hasAudio': False}]}})

    def test_oversized_720p_format_falls_back_to_a_smaller_video(self):
        codecs = {'ext': 'mp4', 'vcodec': 'avc1', 'acodec': 'mp4a'}
        formats = [
            dict(codecs, format_id='360', height=360, filesize=MAX_MEDIA_BYTES // 2),
            dict(codecs, format_id='720', height=720, filesize=MAX_MEDIA_BYTES + 1),
        ]
        with YoutubeDL({'quiet': True}) as downloader:
            original = downloader._select_formats(formats, downloader.build_format_selector(DEFAULT_FORMAT))
            selected = downloader._select_formats(formats, downloader.build_format_selector(youtube.YOUTUBE_FORMAT))
        self.assertEqual(original[0]['format_id'], '720')
        self.assertEqual(selected[0]['format_id'], '360')
