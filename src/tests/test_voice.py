import json
from pathlib import Path
import sys
import threading
import unittest
import urllib.error
import urllib.request
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from runtime import make_server
from voice_engine import VoiceEngine, VoiceError, validate_reply


class VoiceSafetyTests(unittest.TestCase):
    def test_prediction_cannot_execute_verification_branch(self):
        self.assertEqual(validate_reply('{"branch":"tiger","reply":"先记下你的猜想！"}', 'prediction')['branch'],'tiger')
        with self.assertRaises(VoiceError):
            validate_reply('{"branch":"hide","reply":"藏起来！"}', 'prediction')
        with self.assertRaises(VoiceError):
            validate_reply('{"branch":"fox","reply":"猜狐狸。"}', 'method')

    def test_start_context_reaches_engine_without_opening_microphone(self):
        server=make_server(0)
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        try:
            url=f'http://127.0.0.1:{server.server_port}/api/voice/start'
            with patch('runtime.ENGINE.start',return_value={'phase':'recording'}) as start:
                request=urllib.request.Request(url,data=b'{"interaction":"prediction"}',
                                               headers={'X-Stage-Control':'1','Content-Type':'application/json'})
                with urllib.request.urlopen(request,timeout=3) as response:
                    self.assertEqual(response.status,200)
                start.assert_called_once_with('prediction')
            with patch('runtime.ENGINE.start',return_value={'phase':'recording','automatic':True}) as start:
                request=urllib.request.Request(url,data=b'{"interaction":"method","automatic":true}',headers={'X-Stage-Control':'1','Content-Type':'application/json'})
                with urllib.request.urlopen(request,timeout=3) as response:self.assertEqual(response.status,200)
                start.assert_called_once_with('method',automatic=True)
            request=urllib.request.Request(url,data=b'{"automatic":"yes"}',headers={'X-Stage-Control':'1','Content-Type':'application/json'})
            with self.assertRaises(urllib.error.HTTPError) as bad:
                urllib.request.urlopen(request,timeout=3)
            self.assertEqual(bad.exception.code,400)
            request=urllib.request.Request(url,data=b'not-json',headers={'X-Stage-Control':'1'})
            with self.assertRaises(urllib.error.HTTPError) as error:
                urllib.request.urlopen(request,timeout=3)
            self.assertEqual(error.exception.code,400)
        finally:
            server.shutdown();server.server_close();thread.join()

    def test_only_prepared_branches_are_accepted(self):
        for branch in ("hide", "alone", "clarify"):
            self.assertEqual(validate_reply(json.dumps({"branch":branch,"reply":"咱们试一试！"}))["branch"],branch)
        for content in ('{"branch":"shell","reply":"run"}', '[]', 'not json',
                        '{"branch":"hide","reply":null}'):
            with self.assertRaises(VoiceError):
                validate_reply(content)

    def test_cancelled_job_cannot_publish_late_result(self):
        engine = VoiceEngine()
        engine.job = "old"
        engine.cancel()
        self.assertFalse(engine._publish("old",phase="done",branch="hide"))
        self.assertEqual(engine.snapshot()["phase"],"idle")

    def test_external_page_cannot_start_or_cancel_microphone(self):
        server = make_server(0)
        thread = threading.Thread(target=server.serve_forever,daemon=True)
        thread.start()
        try:
            url = f"http://127.0.0.1:{server.server_port}/api/voice/cancel"
            for headers in ({}, {"X-Stage-Control":"1","Origin":"https://example.com"},
                            {"X-Stage-Control":"1","Origin":"http://127.0.0.1:bad"}):
                with self.assertRaises(urllib.error.HTTPError) as result:
                    urllib.request.urlopen(urllib.request.Request(url,method="POST",headers=headers),timeout=3)
                self.assertEqual(result.exception.code,403)
            request = urllib.request.Request(url,method="POST",headers={"X-Stage-Control":"1"})
            with urllib.request.urlopen(request,timeout=3) as response:
                self.assertEqual(json.load(response)["phase"],"idle")
        finally:
            server.shutdown()
            server.server_close()
            thread.join()


if __name__ == "__main__":
    unittest.main()
