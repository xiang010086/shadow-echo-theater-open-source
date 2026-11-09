"""Real v3 clips: idle loop, keyboard replies, muted voice wait, curtain return.

ASR/AI are mocked explicitly; this does not certify a live microphone trial.
"""
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
    data=io.BytesIO()
    with wave.open(data,'wb') as w:
        w.setnchannels(1);w.setsampwidth(2);w.setframerate(16000);w.writeframes(bytes(9600))
    context={'phase':'idle','interaction':'method'};errors=[]
    try:
        with sync_playwright() as p:
            browser=p.chromium.launch(channel='msedge',headless=True,args=['--autoplay-policy=no-user-gesture-required'])
            page=browser.new_page(viewport={'width':1280,'height':720})
            page.on('pageerror',lambda x:errors.append(str(x)))
            page.route('**/media/runtime-voice/*.wav',lambda route:route.fulfill(body=data.getvalue(),content_type='audio/wav'))
            def api(route):
                action=route.request.url.rsplit('/',1)[-1]
                if action=='start':context.update(phase='recording',interaction=route.request.post_data_json['interaction'])
                elif action=='stop':context['phase']='done'
                elif action=='cancel':context['phase']='idle'
                result={'phase':context['phase'],'ready':True}
                if context['phase']=='done':
                    result.update(branch='alone',response='好，请老虎自己上前！',audio='media/runtime-voice/'+'c'*32+'.wav')
                route.fulfill(json=result)
            page.route('**/api/voice/*',api)
            page.goto(f'http://127.0.0.1:{server.server_port}')
            def current(name):
                page.wait_for_function('(name)=>document.querySelector("#stage").currentSrc.endsWith("/"+name+".mp4")',arg=name,timeout=15000)
                page.wait_for_function('document.querySelector("#stage").readyState>=2')
            def finish(name,next_name):
                current(name)
                assert not page.locator('#stage').evaluate('(v)=>v.loop')
                page.locator('#stage').evaluate('(v)=>v.currentTime=Math.max(0,v.duration-.08)')
                current(next_name)
            for method in ['voice-alone','keyboard-hide']:
                current('idle');assert page.locator('#stage').evaluate('(v)=>v.loop')
                assert page.locator('body').inner_text()==''
                box=page.locator('#stage').bounding_box();assert box['width']==1280 and box['height']==720
                page.keyboard.press('Enter')
                finish('welcome','opening');finish('opening','prediction');finish('prediction','prediction_wait')
                assert page.locator('#stage').evaluate('(v)=>v.loop')
                # Waiting does not pick an answer or run the next scene by itself.
                page.wait_for_timeout(450)
                current('prediction_wait')
                page.keyboard.press('2');finish('prediction_reply','question');finish('question','method_wait')
                if method=='voice-alone':
                    page.keyboard.down('Space')
                    page.wait_for_function('document.querySelector("#stage").muted===true')
                    page.keyboard.up('Space');current('alone')
                    assert not page.locator('#stage').evaluate('(v)=>v.muted')
                    finish('alone','ending')
                else:
                    page.keyboard.press('1');finish('method_reply','hide');finish('hide','ending')
                finish('ending','curtain');finish('curtain','idle')
                assert not page.locator('#error').is_visible()
            assert not errors,errors
            browser.close()
        print('PASS: v3 real playback, full-screen no text, idle loop, two waits, both branches, voice ducking, curtain and return. ASR/AI mocked.')
    finally:
        server.shutdown();server.server_close();thread.join()


if __name__=='__main__':main()
