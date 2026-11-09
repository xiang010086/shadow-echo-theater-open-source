import json
from pathlib import Path
import sys
import threading
import unittest
import urllib.error
import urllib.request

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from runtime import make_server, PUBLIC


class ServiceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = make_server(0)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.url = 'http://127.0.0.1:{}'.format(cls.server.server_port)

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()

    def get(self, path, range_header=None, method='GET'):
        headers = {'Range': range_header} if range_header else {}
        return urllib.request.urlopen(urllib.request.Request(self.url + path, headers=headers, method=method))

    def test_health(self):
        with self.get('/health') as response:
            self.assertTrue(json.load(response)['ok'])

    def test_module_mime_is_platform_independent(self):
        for module in ('app.mjs', 'state.mjs'):
            with self.get('/' + module) as response:
                self.assertEqual(response.headers.get_content_type(), 'application/javascript')

    def test_all_manifest_media_present(self):
        config = json.loads((PUBLIC / 'config.json').read_text())
        for path in config['clips'].values():
            with self.get('/' + path) as response:
                self.assertEqual(response.headers.get_content_type(), 'video/mp4')
                self.assertGreater(int(response.headers['Content-Length']), 100)

    def test_ranges(self):
        data = (PUBLIC / 'media' / 'welcome.mp4').read_bytes()
        for header, expected in [('bytes=0-19', data[:20]), ('bytes=-12', data[-12:]), ('bytes=10-', data[10:])]:
            with self.get('/media/welcome.mp4', header) as response:
                self.assertEqual(response.status, 206)
                self.assertEqual(response.read(), expected)
        with self.get('/media/welcome.mp4', 'bytes=0-19', method='HEAD') as response:
            self.assertEqual(response.headers['Content-Length'], '20')
            self.assertEqual(response.read(), b'')

    def test_bad_range_and_missing_file(self):
        for path, header, expected in [('/media/welcome.mp4', 'bytes=999999999-', 416), ('/media/welcome.mp4', 'bytes=5-2', 416), ('/media/welcome.mp4', 'bytes=-0', 416), ('/missing.mp4', None, 404), ('/media/', None, 403)]:
            with self.assertRaises(urllib.error.HTTPError) as error:
                self.get(path, header)
            self.assertEqual(error.exception.code, expected)


if __name__ == '__main__':
    unittest.main()
