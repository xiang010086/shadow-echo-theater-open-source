"""Local-only stage playback service; no third-party dependencies."""

import argparse
import functools
import http.server
import json
from pathlib import Path
import re
from urllib.parse import urlsplit

from voice_engine import ENGINE, VoiceError

PUBLIC = Path(__file__).resolve().parent / "public"


class StageHandler(http.server.SimpleHTTPRequestHandler):
    def send_json(self, body, status=200):
        content = json.dumps(body, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def do_POST(self):
        # A web page on another origin must not start the room microphone.
        origin = self.headers.get("Origin")
        try:
            parsed = urlsplit(origin) if origin else None
            origin_port = parsed.port if parsed else None
        except ValueError:
            self.send_json({"error":"Forbidden"}, 403)
            return
        if (self.headers.get("X-Stage-Control") != "1" or
                (parsed and (parsed.scheme != "http" or parsed.hostname != "127.0.0.1"
                             or origin_port != self.server.server_port))):
            self.send_json({"error":"Forbidden"}, 403)
            return
        actions = {"/api/voice/start":ENGINE.start, "/api/voice/stop":ENGINE.stop,
                   "/api/voice/cancel":ENGINE.cancel}
        action = actions.get(self.path)
        if action is None:
            self.send_json({"error":"Not found"}, 404)
            return
        try:
            if self.path == '/api/voice/start':
                length = int(self.headers.get('Content-Length', '0'))
                if not 0 <= length <= 1024:
                    self.send_json({'error':'Invalid request length'}, 400)
                    return
                payload = json.loads(self.rfile.read(length)) if length else {}
                if not isinstance(payload, dict):
                    raise ValueError('Invalid request')
                if 'automatic' in payload:
                    if type(payload['automatic']) is not bool:raise ValueError('Invalid capture mode')
                    self.send_json(ENGINE.start(payload.get('interaction','method'),automatic=payload['automatic']))
                else:
                    self.send_json(ENGINE.start(payload.get('interaction', 'method')))
            else:
                self.send_json(action())
        except VoiceError as error:
            self.send_json({"error":str(error)}, 409)
        except (ValueError, TypeError):
            self.send_json({'error':'Invalid request'}, 400)

    def end_headers(self):
        # Local kiosk assets are replaced during deployment. Always fetch the
        # current version, including imported ES modules and video clips.
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def guess_type(self, path):
        if Path(path).suffix.lower() in (".mjs", ".js"):
            return "application/javascript"
        return super().guess_type(path)

    def __init__(self, *args, **kwargs):
        self.byte_range = None
        super().__init__(*args, **kwargs)

    def do_GET(self):
        if self.path == "/api/voice/status":
            self.send_json(ENGINE.snapshot())
            return
        if self.path == "/health":
            body = json.dumps({"ok": True, "mode": "offline-test", "version": "0.5-two-interactions", "service":"yingyouhuisheng"}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        super().do_GET()

    def list_directory(self, path):
        self.send_error(403, "Directory listing disabled")
        return None

    def send_head(self):
        self.byte_range = None
        path = Path(self.translate_path(self.path))
        try:
            path.resolve().relative_to(PUBLIC.resolve())
        except ValueError:
            self.send_error(403)
            return None
        header = self.headers.get("Range")
        if not header or not path.is_file():
            return super().send_head()
        size = path.stat().st_size
        match = re.fullmatch(r"bytes=(\d*)-(\d*)", header.strip())
        if not match or not any(match.groups()) or size == 0:
            return self.bad_range(size)
        first, last = match.groups()
        if first:
            start = int(first)
            end = min(int(last), size - 1) if last else size - 1
        else:
            suffix = int(last)
            if suffix == 0:
                return self.bad_range(size)
            start, end = max(0, size - suffix), size - 1
        if start >= size or end < start:
            return self.bad_range(size)
        try:
            stream = path.open("rb")
        except OSError:
            self.send_error(404)
            return None
        self.byte_range = (start, end)
        self.send_response(206)
        self.send_header("Content-Type", self.guess_type(str(path)))
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Content-Range", "bytes {}-{}/{}".format(start, end, size))
        self.send_header("Content-Length", str(end - start + 1))
        self.end_headers()
        stream.seek(start)
        return stream

    def bad_range(self, size):
        self.send_response(416)
        self.send_header("Content-Range", "bytes */{}".format(size))
        self.send_header("Content-Length", "0")
        self.end_headers()
        return None

    def copyfile(self, source, outputfile):
        try:
            if self.byte_range is None:
                return super().copyfile(source, outputfile)
            remaining = self.byte_range[1] - self.byte_range[0] + 1
            while remaining:
                block = source.read(min(65536, remaining))
                if not block:
                    break
                outputfile.write(block)
                remaining -= len(block)
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
            # Clients may close a previous range when seeking or switching.
            return


def make_server(port=8765):
    handler = functools.partial(StageHandler, directory=str(PUBLIC))
    return http.server.ThreadingHTTPServer(("127.0.0.1", port), handler)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    with make_server(args.port) as server:
        print("Stage test: http://127.0.0.1:{} (Ctrl+C to stop)".format(server.server_port), flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass


if __name__ == "__main__":
    main()
