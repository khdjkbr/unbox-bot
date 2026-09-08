import unittest
from unittest.mock import AsyncMock, patch
from services import youtube

class CascadeTests(unittest.IsolatedAsyncioTestCase):
    async def test_success_does_not_spend_api_quota(self):
        with patch.object(youtube, 'download_media', AsyncMock(return_value='video.mp4')), patch.object(youtube, '_yoinku', AsyncMock()) as fallback:
            self.assertEqual(await youtube.download_youtube('url'), 'video.mp4')
            fallback.assert_not_awaited()

    async def test_failure_uses_configured_fallback(self):
        with patch.object(youtube, 'download_media', AsyncMock(side_effect=RuntimeError('403'))), patch.object(youtube, '_yoinku', AsyncMock(return_value='fallback.mp4')) as fallback, patch.dict('os.environ', {'YOINKU_API_KEY': 'test'}):
            self.assertEqual(await youtube.download_youtube('url'), 'fallback.mp4')
            fallback.assert_awaited_once_with('url', 'test')

    def test_video_without_audio_is_rejected(self):
        with self.assertRaises(RuntimeError):
            youtube._format({'data': {'formats': [{'container': 'mp4', 'height': 720, 'hasVideo': True, 'hasAudio': False}]}})
