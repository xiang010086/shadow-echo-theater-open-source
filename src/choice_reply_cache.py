"""Local spoken acknowledgements for the four finite story choices.

AI still interprets non-explicit answers. Clarifications use existing local
question prompts; no additional network speech synthesis is needed to retry.
"""
from pathlib import Path
import wave
import re

ROOT=Path(__file__).resolve().parent/'public/media/choice-replies'
TEXT={
    ('prediction','fox'):'你猜是狐狸，咱们用证据说话！',
    ('prediction','tiger'):'你猜是老虎，咱们用证据说话！',
    ('method','hide'):'好，就让老虎藏好，看看狐狸的威风！',
    ('method','alone'):'好，狐狸留下，请老虎自己上前！',
}


def explicit_choice(text,interaction):
    """Exact, unambiguous choices only; negation/reasons go to the AI model."""
    if not isinstance(text,str):return None
    value=re.sub(r'[\s，。！？、,.!?]','',text).lower()
    letter={x:'first' for x in ['a','选a','我选a','选择a','选第一个','我选第一个']}
    letter.update({x:'second' for x in ['b','选b','我选b','选择b','选第二个','我选第二个']})
    if interaction=='prediction':
        first={'狐狸','怕狐狸','我猜狐狸','我选狐狸','我猜是狐狸'}
        second={'老虎','怕老虎','我猜老虎','我选老虎','我猜是老虎'}
        branches=('fox','tiger')
    elif interaction=='method':
        first={'藏起来','老虎藏好','老虎藏起来','让老虎藏好','让老虎藏起来','我想让老虎藏起来','狐狸自己过去'}
        second={'老虎自己去','老虎自己过去','老虎独自过去','让老虎自己去','让老虎自己过去'}
        branches=('hide','alone')
    else:return None
    if value in first or letter.get(value)=='first':return branches[0]
    if value in second or letter.get(value)=='second':return branches[1]
    return None


def lookup(interaction,branch):
    if branch=='clarify' and interaction in {'prediction','method'}:
        path=ROOT.parent/'voice-prompts'/f'{interaction}.wav'
        text='没听清，请再说说：你猜狐狸还是老虎？' if interaction=='prediction' else '没听清，请再说说：让老虎藏好，还是独自过去？'
    else:
        text=TEXT.get((interaction,branch))
        path=ROOT/f'{interaction}-{branch}.wav'
    if not text:return None
    try:
        with wave.open(str(path),'rb') as w:
            if not .2<w.getnframes()/w.getframerate()<20:return None
    except (OSError,EOFError,wave.Error):return None
    return {'text':text,'path':path}
