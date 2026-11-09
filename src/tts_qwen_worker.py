"""Qwen demo worker using the account token supplied for this project."""
import json
import os
from pathlib import Path
import shutil
import sys
import wave

from gradio_client import Client
from huggingface_access import load_token

HOST_STYLE='用普通话，像热情机灵的小戏班班主在招呼观众。带笑意，句子抑扬顿挫，亲切、有精神、有自然停顿。保留戏班口吻与自然儿化，字的起音和收尾完整，减少连读吞字，关键短语有轻微停顿。不要机械朗读，不唱歌。'

if __name__=='__main__':
    request=json.load(sys.stdin)
    os.environ['GRADIO_ANALYTICS_ENABLED']='False'
    token=load_token()
    if not token:raise RuntimeError('Hugging Face token has not been provided')
    client=Client('Qwen/Qwen3-TTS',token=token,verbose=False,analytics_enabled=False)
    result=client.predict(request['text'],'Chinese',request.get('speaker','Dylan'),
                          request.get('instruct',HOST_STYLE),'1.7B',
                          api_name='/generate_custom_voice')
    if not result or not result[0]:raise RuntimeError('No generated speech returned')
    source=Path(result[0])
    with wave.open(str(source),'rb') as audio:
        if audio.getnframes()<100:raise ValueError('Empty generated speech')
    destination=Path(request['destination'])
    shutil.copyfile(source,destination)
    print(json.dumps({'ok':True,'status':result[1]}))
