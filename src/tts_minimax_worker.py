"""MiniMax official China speech API; no implicit credentials or retries."""
import io
import json
from pathlib import Path
import sys
import urllib.error
import urllib.request
import wave

KEY_FILE = Path(__file__).resolve().parent / '.private/minimax_key.txt'
ENDPOINT = 'https://api.minimax.cn/v1/t2a_v2'
MODEL = 'speech-2.8-hd'
HOST_PROFILE = KEY_FILE.parent / 'minimax_host_clone.json'
BLOCK_FILE = KEY_FILE.parent / 'minimax_tts_blocked.json'


def balance_blocked():
    return BLOCK_FILE.is_file()


class SpeechError(Exception):
    pass


def host_profile():
    try:
        profile = json.loads(HOST_PROFILE.read_text(encoding='utf-8'))
        if profile.get('user_approved') and isinstance(profile.get('voice_id'), str):
            return profile
    except (OSError, ValueError, AttributeError):
        pass
    return {}


def host_ready():
    return bool(load_key() and host_profile().get('voice_id'))


def load_key():
    try:
        key = KEY_FILE.read_text(encoding='utf-8-sig').strip()
    except OSError:
        return ''
    return key if len(key) > 10 and not any(c.isspace() for c in key) else ''


def build_payload(request):
    text, voice = request.get('text'), request.get('speaker')
    speed, pitch = request.get('speed', .96), request.get('pitch', 0)
    emotion = request.get('emotion', 'happy')
    blend = request.get('timbre_weights')
    if blend is not None:
        if (not isinstance(blend, list) or not 1 <= len(blend) <= 4
                or any(not isinstance(row, dict)
                       or not isinstance(row.get('voice_id'), str)
                       or not 1 <= len(row['voice_id']) <= 120
                       or type(row.get('weight')) is not int
                       or not 1 <= row['weight'] <= 100 for row in blend)):
            raise SpeechError('MiniMax混合音色参数不正确。')
    if (not isinstance(text, str) or not 1 <= len(text) < 10000
            or not isinstance(voice, str) or (not voice and not blend) or len(voice) > 120
            or not isinstance(speed, (int, float)) or not .5 <= speed <= 2
            or not isinstance(pitch, int) or not -12 <= pitch <= 12
            or emotion not in {None, 'happy', 'sad', 'angry', 'fearful', 'disgusted',
                               'surprised', 'calm', 'fluent', 'whisper'}):
        raise SpeechError('MiniMax配音参数不正确。')
    payload = {'model': MODEL, 'text': text, 'stream': False, 'output_format': 'hex',
            'language_boost': 'Chinese', 'subtitle_enable': False,
            'voice_setting': {'voice_id': '' if blend else voice, 'speed': speed,
                              'vol': 1, 'pitch': pitch},
            'audio_setting': {'sample_rate': 32000, 'format': 'wav', 'channel': 1},
            'pronunciation_dict': {'tone': ['小班主/(xiao3)(ban1)(zhu3)',
                                           '狐假虎威/(hu2)(jia3)(hu3)(wei1)']}}
    if emotion is not None:
        payload['voice_setting']['emotion'] = emotion
    if blend:
        payload['timbre_weights'] = [dict(voice_id=row['voice_id'], weight=row['weight'])
                                     for row in blend]
    return payload


def synthesize(request):
    if balance_blocked():
        raise SpeechError('MiniMax余额不足（1008）；补充可用余额后再恢复生成。')
    key = load_key()
    if not key:
        raise SpeechError('MiniMax密钥尚未配置。')
    payload = build_payload(request)
    destination = Path(request['destination'])
    call = urllib.request.Request(ENDPOINT, data=json.dumps(payload).encode('utf-8'),
                                  headers={'Content-Type': 'application/json',
                                           'Authorization': 'Bearer ' + key})
    try:
        with urllib.request.urlopen(call, timeout=65) as response:
            raw = response.read(16_000_001)
    except urllib.error.HTTPError as error:
        raise SpeechError(f'MiniMax返回HTTP {error.code}；已停止，没有自动重试。') from None
    if len(raw) > 16_000_000:
        raise SpeechError('MiniMax返回音频过大。')
    result = json.loads(raw)
    status = result.get('base_resp') or {}
    if status.get('status_code') != 0:
        if status.get('status_code') == 1008:
            BLOCK_FILE.write_text(json.dumps({'provider':'minimax','reason':'balance','code':1008}),encoding='utf-8')
        message = str(status.get('status_msg', '无状态说明')).replace(key, '[REDACTED]')[:200]
        raise SpeechError(f'MiniMax返回{status.get("status_code", "未知状态")}：{message}')
    data = result.get('data') or {}
    if data.get('status') != 2 or not isinstance(data.get('audio'), str):
        raise SpeechError('MiniMax未返回完整音频。')
    audio = bytes.fromhex(data['audio'])
    try:
        with wave.open(io.BytesIO(audio), 'rb') as reader:
            if reader.getnframes() < 100:
                raise SpeechError('MiniMax返回空音频。')
            duration = reader.getnframes() / reader.getframerate()
    except (wave.Error, EOFError):
        raise SpeechError('MiniMax返回的WAV音频不可读。') from None
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(audio)
    return {'ok': True, 'source': ENDPOINT, 'model': MODEL,
            'speaker': payload['voice_setting']['voice_id'],
            'duration': duration, 'usage': result.get('extra_info', {})}


if __name__ == '__main__':
    try:
        request = json.load(sys.stdin)
        if 'speaker' not in request:
            request.update(speaker=host_profile().get('voice_id'), emotion=None, speed=1.0)
        print(json.dumps(synthesize(request), ensure_ascii=False))
    except SpeechError as error:
        print(str(error), file=sys.stderr)
        sys.exit(1)
    except (OSError, ValueError, KeyError, TypeError):
        print('MiniMax配音未完成；已停止，没有自动重试。', file=sys.stderr)
        sys.exit(1)
