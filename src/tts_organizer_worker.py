"""Competition-funded Qwen TTS over the documented OpenAI-compatible base URL."""
import io
import json
from pathlib import Path
import sys
import wave

import requests

KEY_FILE=Path(__file__).resolve().parent/'.private/organizer_key.txt'
ENDPOINT='https://api.openai-next.com/v1/audio/speech'
MODEL='qwen3-tts-flash'


class SpeechError(Exception):
    pass


def load_key():
    try:
        value=KEY_FILE.read_text(encoding='utf-8-sig').strip()
    except OSError:
        return ''
    return value if value.startswith('sk-') and not any(c.isspace() for c in value) else ''


def normalize_wav(raw):
    # The gateway returns a streaming RIFF header with a placeholder length.
    # Rebuild it from actual PCM bytes so players do not show a 12-hour duration.
    with wave.open(io.BytesIO(raw),'rb') as reader:
        channels,width,rate=reader.getnchannels(),reader.getsampwidth(),reader.getframerate()
        frames=reader.readframes(min(reader.getnframes(),rate*180))
    if not frames or len(frames) < width*channels*rate*.1:
        raise SpeechError('比赛语音返回空音频。')
    output=io.BytesIO()
    with wave.open(output,'wb') as writer:
        writer.setnchannels(channels);writer.setsampwidth(width);writer.setframerate(rate)
        writer.writeframes(frames)
    return output.getvalue(),len(frames)/(width*channels*rate)


def synthesize(request):
    key=load_key()
    if not key:
        raise SpeechError('比赛服务密钥尚未配置。')
    text=request.get('text');voice=request.get('speaker','Dylan')
    if not isinstance(text,str) or not 1 <= len(text) <= 600 or not isinstance(voice,str) or not voice:
        raise SpeechError('比赛语音请求参数不正确。')
    payload={'model':MODEL,'input':text,'voice':voice,'response_format':'wav'}
    try:
        with requests.post(ENDPOINT,headers={'Authorization':'Bearer '+key,
                           'User-Agent':'YingYouHuiSheng/1.0'},json=payload,timeout=50,stream=True) as response:
            if not response.ok:
                raise SpeechError(f'比赛配音返回HTTP {response.status_code}，已停止，没有自动重试。')
            chunks=[];size=0
            for chunk in response.iter_content(65536):
                size+=len(chunk)
                if size>20_000_000:raise SpeechError('比赛配音文件过大。')
                chunks.append(chunk)
        audio,duration=normalize_wav(b''.join(chunks))
    except requests.RequestException:
        raise SpeechError('比赛配音连接未完成，已停止，没有自动重试。') from None
    destination=Path(request['destination']);destination.parent.mkdir(parents=True,exist_ok=True)
    destination.write_bytes(audio)
    return {'ok':True,'source':ENDPOINT,'model':MODEL,'speaker':voice,'duration':duration}


if __name__=='__main__':
    try:
        print(json.dumps(synthesize(json.load(sys.stdin)),ensure_ascii=False))
    except SpeechError as error:
        print(str(error),file=sys.stderr);sys.exit(1)
    except (OSError,ValueError,TypeError,KeyError,wave.Error,EOFError):
        print('比赛配音未完成，已停止，没有自动重试。',file=sys.stderr);sys.exit(1)
