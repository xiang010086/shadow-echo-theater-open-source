"""Auto listen lifecycle with explicitly mocked microphone/AI responses."""
import io
import json
from pathlib import Path
import sys
import threading
import wave
from playwright.sync_api import sync_playwright

PROGRAM=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(PROGRAM))
from runtime import make_server


def main():
    server=make_server(0);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    config=json.loads((PROGRAM/'public/config.test.json').read_text(encoding='utf-8'))
    config.update(twoInteractions=True,testMedia=False,autoListen=True,
                  voicePrompts={x:f'media/voice-prompts/{x}.wav' for x in ['prediction','method','unavailable']})
    config['clips']['prediction']=config['clips']['question']
    audio=io.BytesIO()
    with wave.open(audio,'wb') as w:w.setnchannels(1);w.setsampwidth(2);w.setframerate(16000);w.writeframes(bytes(6400))
    starts=[];errors=[];context={'phase':'idle','interaction':'method','polls':0,'fail':False}
    try:
        with sync_playwright() as p:
            browser=p.chromium.launch(channel='msedge',headless=True,args=['--autoplay-policy=no-user-gesture-required'])
            page=browser.new_page();page.on('pageerror',lambda x:errors.append(str(x)))
            page.route('**/config.json',lambda route:route.fulfill(json=config))
            for pattern in ['**/media/runtime-voice/*.wav','**/media/voice-prompts/*.wav']:
                page.route(pattern,lambda route:route.fulfill(body=audio.getvalue(),content_type='audio/wav'))
            def api(route):
                action=route.request.url.rsplit('/',1)[-1]
                if action=='start':
                    payload=route.request.post_data_json;assert payload.get('automatic') is True
                    starts.append(payload['interaction']);context.update(phase='recording',interaction=payload['interaction'],polls=0)
                if action=='cancel':context['phase']='idle'
                if action=='status' and context['phase']=='recording':
                    context['polls']+=1
                    if context['polls']>=3:context['phase']='error' if context['fail'] else 'done'
                result={'phase':context['phase'],'ready':True}
                if context['phase']=='recording':result.update(listening_ready=True,speech_detected=False)
                if context['phase']=='done':result.update(branch='tiger' if context['interaction']=='prediction' else 'hide',response='好，咱们验证！',audio='media/runtime-voice/'+'d'*32+'.wav')
                if context['phase']=='error':result['error']='没有听清。'
                route.fulfill(json=result)
            page.route('**/api/voice/*',api)
            page.goto(f'http://127.0.0.1:{server.server_port}')
            page.wait_for_function('!document.querySelector("#start").disabled')
            page.wait_for_timeout(900);assert not starts,'opened mic during idle'
            page.keyboard.press('Enter')
            page.wait_for_function('document.querySelector("#status").textContent.includes("本轮完成")',timeout=25000)
            assert starts==['prediction','method'],starts
            page.keyboard.press('0');context['fail']=True
            page.keyboard.press('Enter')
            page.wait_for_function('!document.querySelector("#choices").hidden',timeout=12000)
            page.wait_for_function('document.querySelector("#audience-message").textContent.includes("我在听")')
            assert page.locator('#audience-feedback').is_visible(),'audience cannot see listening status in full-screen show mode'
            page.wait_for_timeout(6500)
            assert starts==['prediction','method','prediction','prediction','prediction'],starts
            assert not page.locator('#choices').evaluate('(x)=>x.hidden'),'picked answer after silence/error'
            assert page.locator('#retry-listen').is_visible(),'retry exhaustion silently abandoned the audience'
            before_retry=len(starts)
            page.locator('#retry-listen').click();page.wait_for_timeout(1100)
            assert len(starts)>before_retry,'mouse click did not restart automatic listening after retries'
            page.keyboard.press('0');page.wait_for_timeout(900)
            after_reset=len(starts);page.wait_for_timeout(900)
            assert len(starts)==after_reset,'reset failed to cancel auto start'
            assert not errors,errors;browser.close()
        print('PASS: automatic requests at both choices, none during idle, retries capped at three, no guessed answer, reset cancellation. Mic/AI mocked.')
    finally:server.shutdown();server.server_close();thread.join()


if __name__=='__main__':main()
