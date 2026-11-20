import asyncio
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from aiogram.exceptions import TelegramBadRequest
from aiogram.methods import EditMessageText

from handlers import media
from services import database, downloader
from services.http_download import save_response
from services.links import extract_link


class RegressionTests(unittest.IsolatedAsyncioTestCase):
    def test_domain_validation(self):
        self.assertIsNone(extract_link('https://evil.test/instagram.com/reel/a'))
        self.assertIsNone(extract_link('https://instagram.com.evil.test/reel/a'))
        self.assertEqual(extract_link('video https://WWW.Instagram.com/reel/a/.'),
                         ('https://WWW.Instagram.com/reel/a/', 'instagram'))

    def test_missing_user_has_zero_downloads(self):
        with tempfile.TemporaryDirectory() as folder:
            with patch.object(database, 'DB_PATH', str(Path(folder) / 'db.sqlite')):
                self.assertEqual(database.get_user_and_global_stats(123)['user_downloads'], 0)
                database.add_user(123, 'name')
                database.add_user(123)
                database.increment_download(123)
                self.assertEqual(database.get_stats()['total_downloads'], 1)

    async def test_interrupted_http_download_is_removed(self):
        async def chunks(size):
            yield b'partial'
            raise OSError('connection lost')
        response = SimpleNamespace(raise_for_status=lambda: None,
                                   content=SimpleNamespace(iter_chunked=chunks))
        with tempfile.TemporaryDirectory() as folder:
            path = str(Path(folder) / 'file.mp4')
            with self.assertRaises(OSError):
                await save_response(response, path)
            self.assertFalse(Path(path).exists())

    async def test_upload_failure_cleans_file_and_does_not_count(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'file.mp4'
            path.write_bytes(b'video')
            progress = SimpleNamespace(edit_text=AsyncMock())
            message = SimpleNamespace(
                text='https://www.instagram.com/reel/test/', caption=None,
                message_id=10,
                from_user=SimpleNamespace(id=123, username='tester'),
                chat=SimpleNamespace(id=123, type='private'),
                bot=SimpleNamespace(send_chat_action=AsyncMock()),
                answer=AsyncMock(return_value=progress),
                answer_video=AsyncMock(side_effect=RuntimeError('upload failed')),
            )
            with patch.object(media, 'add_user'), \
                 patch.object(media, 'check_subscription', AsyncMock(return_value=True)), \
                 patch.object(media, 'download_instagram', AsyncMock(return_value=str(path))), \
                 patch.object(media, 'convert_for_ios', return_value=str(path)), \
                 patch.object(media, 'increment_download') as increment:
                await media.handle_links(message)
                increment.assert_not_called()
                progress.edit_text.assert_awaited_once()
                sent = message.answer_video.await_args.kwargs
                self.assertEqual(sent['parse_mode'], 'HTML')
                self.assertEqual(sent['reply_parameters'].message_id, 10)
                self.assertTrue(sent['reply_parameters'].allow_sending_without_reply)
            self.assertFalse(path.exists())

    async def test_removed_progress_message_still_reports_failure(self):
        missing_message = TelegramBadRequest(
            method=EditMessageText(text='failed'), message='message to edit not found'
        )
        progress = SimpleNamespace(edit_text=AsyncMock(side_effect=missing_message))
        message = SimpleNamespace(answer=AsyncMock())

        await media.report_download_error(message, progress, 'Download failed')

        message.answer.assert_awaited_once_with('Download failed')

    def test_final_file_selected_and_fragments_removed(self):
        folders = []
        class FakeDownloader:
            def __init__(self, options):
                self.folder = Path(options['outtmpl']).parent
                folders.append(self.folder)
            def __enter__(self):
                return self
            def __exit__(self, *args):
                pass
            def add_post_processor(self, capture, when):
                self.capture = capture
            def download(self, urls):
                (self.folder / 'partial.mp4.part').write_bytes(b'bad')
                final = self.folder / 'final.mp4'
                final.write_bytes(b'complete')
                self.capture.run({'filepath': str(final)})
        with patch.object(downloader.yt_dlp, 'YoutubeDL', FakeDownloader):
            path = Path(downloader.download_sync('https://instagram.com/reel/test/'))
        try:
            self.assertEqual(path.read_bytes(), b'complete')
            self.assertFalse(folders[0].exists())
        finally:
            path.unlink()


if __name__ == '__main__':
    unittest.main()
