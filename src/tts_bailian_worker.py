"""One-shot official Beijing Qwen TTS audition; no automatic retries.

Reference: https://help.aliyun.com/zh/model-studio/qwen-tts-api
Not selected by the live player until voice compatibility is auditioned.
"""
import io
import json
from pathlib import Path
import re
import sys
import urllib.error
import urllib.request
from urllib.parse import urlsplit, urlunsplit
import wave

KEY_FILE = Path(__file__).resolve().parent / '.private/bailian_key.txt'
ENDPOINT = 'https://dashscope.aliyuncs.com/api/v1/services/aigc/multimodal-generation/generation'
MODEL = 'qwen3-tts-instruct-flash'


class SpeechError(Exception):
    pass


def load_key():
    try:
        key = KEY_FILE.read_text(encoding='utf-8-sig').strip()
    except OSError:
        return ''
    return key if key.startswith('sk-') and not any(c.isspace() for c in key) else ''


def audio_url(value):
    if not isinstance(value, str):
        raise SpeechError('百炼未返回音频地址。')
    url = urlsplit(value)
    if (url.scheme not in {'http', 'https'} or not url.hostname
            or not url.hostname.endswith('.aliyuncs.com')
            or url.username or url.password or url.port not in {None, 443}):
        raise SpeechError('百炼返回了不支持的音频地址。')
    # Official examples return signed OSS URLs over HTTP; use HTTPS to download.
    return urlunsplit(url._replace(scheme='https'))


def synthesize(request):
    key = load_key()
    if not key:
        raise SpeechError('请先把北京地域的百炼API Key保存到.private/bailian_key.txt。')
    text, voice = request.get('text'), request.get('speaker', 'Dylan')
    instruction = request.get('instruct', '')
    if (not isinstance(text, str) or not 1 <= len(text) <= 600
            or not isinstance(voice, str) or not voice or len(voice) > 80
            or not isinstance(instruction, str) or len(instruction) > 1600):
        raise SpeechError('试听文本或音色参数不正确。')
    destination = Path(request['destination'])
    payload = {'model': MODEL, 'input': {
        'text': text, 'voice': voice, 'language_type': 'Chinese',
        'instructions': instruction, 'optimize_instructions': False,
    }}
    call = urllib.request.Request(ENDPOINT, data=json.dumps(payload).encode('utf-8'),
                                  headers={'Content-Type': 'application/json',
                                           'Authorization': 'Bearer ' + key})
    try:
        with urllib.request.urlopen(call, timeout=60) as response:
            raw = response.read(65537)
        if len(raw) > 65536:
            raise SpeechError('百炼返回内容过长。')
        result = json.loads(raw)
    except urllib.error.HTTPError as error:
        raise SpeechError(f'百炼返回HTTP {error.code}；请核对地域、密钥、模型权限及额度。') from None
    if result.get('code') or result.get('status_code', 200) != 200:
        code = re.sub(r'[^a-zA-Z0-9_.-]', '', str(result.get('code', 'Unknown')))[:80]
        raise SpeechError('百炼未完成配音：' + code)
    url = audio_url(result.get('output', {}).get('audio', {}).get('url'))
    # Credentials are sent only to the synthesis endpoint, never to the file URL.
    with urllib.request.urlopen(url, timeout=30) as response:
        audio = response.read(20_000_001)
    if len(audio) > 20_000_000:
        raise SpeechError('返回的音频文件过大。')
    try:
        with wave.open(io.BytesIO(audio), 'rb') as reader:
            if reader.getnframes() < 100:
                raise SpeechError('返回的音频为空。')
    except (wave.Error, EOFError):
        raise SpeechError('返回的音频不是可用的WAV文件。') from None
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(audio)
    return {'ok': True, 'source': ENDPOINT, 'model': MODEL,
            'speaker': voice, 'usage': result.get('usage', {})}


if __name__ == '__main__':
    try:
        print(json.dumps(synthesize(json.load(sys.stdin)), ensure_ascii=False))
    except SpeechError as error:
        print(str(error), file=sys.stderr)
        sys.exit(1)
    except (OSError, ValueError, KeyError, TypeError):
        print('百炼试听未完成；已停止，没有自动重试。', file=sys.stderr)
        sys.exit(1)
