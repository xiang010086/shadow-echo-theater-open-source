"""Real browser/controller tests with explicitly mocked ASR/model responses."""
import io
import json
from pathlib import Path
import sys
import threading
import wave

from playwright.sync_api import sync_playwright

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from runtime import make_server


def main():
    server=make_server(0)
    thread=threading.Thread(target=server.serve_forever,daemon=True)
    thread.start()
    stream=io.BytesIO()
    with wave.open(stream,'wb') as output:
        output.setnchannels(1);output.setsampwidth(2);output.setframerate(16000)
        output.writeframes(bytes(3200))
    state={'phase':'idle','polls':0,'starts':0,'stops':0,'fail':False}
    failures=[]
    try:
        with sync_playwright() as playwright:
            browser=playwright.chromium.launch(channel='msedge',headless=True)
            page=browser.new_page()
            page.on('pageerror',lambda error:failures.append(str(error)))
            page.route('**/config.json',lambda route:route.fulfill(
                path=str(Path(__file__).resolve().parents[1]/'public/config.test.json'),
                content_type='application/json'))
            page.route('**/media/runtime-voice/*.wav',lambda route:route.fulfill(
                body=stream.getvalue(),content_type='audio/wav'))

            def api(route):
                action=route.request.url.rsplit('/',1)[-1]
                if action=='start':
                    state['starts']+=1
                    if state['fail']:
                        route.fulfill(status=409,json={'error':'语音服务尚未配置，可按1/2继续。'})
                        return
                    state['phase']='recording'
                elif action=='stop':
                    state['stops']+=1;state['phase']='thinking';state['polls']=0
                elif action=='cancel':state['phase']='idle'
                elif action=='status' and state['phase']=='thinking':
                    state['polls']+=1
                    if state['polls']>=2:state['phase']='done'
                payload=dict(ready=True,configured=True,phase=state['phase'])
                if state['phase']=='done':
                    payload.update(branch='hide',response='好，让老虎藏好！',transcript='让老虎藏起来',
                                   audio='media/runtime-voice/'+'a'*32+'.wav')
                route.fulfill(json=payload)

            page.route('**/api/voice/*',api)
            page.goto(f'http://127.0.0.1:{server.server_port}')

            def to_choice():
                page.wait_for_function('!document.querySelector("#start").disabled')
                page.locator('#start').click()
                page.locator('#choices').wait_for(state='visible',timeout=15000)

            to_choice()
            # Down and up in one JS turn: release occurs before HTTP start resolves.
            page.evaluate("""() => {
              document.dispatchEvent(new KeyboardEvent('keydown',{code:'Space',key:' '}));
              document.dispatchEvent(new KeyboardEvent('keyup',{code:'Space',key:' '}));
            }""")
            page.wait_for_function('document.querySelector("#stage").currentSrc.endsWith("/hide.mp4")',timeout=10000)
            page.wait_for_function('document.querySelector("#status").textContent.includes("本轮完成")',timeout=10000)
            assert state['starts']==1 and state['stops']==1,state
            page.locator('#reset').click()
            to_choice()
            # A manual choice cancels a pending utterance, and the late response
            # must not replace the selected branch.
            page.evaluate("""() => {
              document.dispatchEvent(new KeyboardEvent('keydown',{code:'Space',key:' '}));
              document.dispatchEvent(new KeyboardEvent('keyup',{code:'Space',key:' '}));
              document.querySelector('#alone').click();
            }""")
            page.wait_for_function('document.querySelector("#stage").currentSrc.endsWith("/alone.mp4")')
            page.wait_for_function('document.querySelector("#status").textContent.includes("本轮完成")',timeout=10000)
            page.locator('#reset').click()
            to_choice()
            state['fail']=True
            page.keyboard.down('Space');page.keyboard.up('Space')
            page.wait_for_function('document.querySelector("#voice-note").textContent.includes("尚未配置")')
            assert page.locator('#choices').is_visible()
            page.locator('#hide').click()
            page.wait_for_function('document.querySelector("#status").textContent.includes("本轮完成")',timeout=10000)
            assert not failures,failures
            browser.close()
            print('PASS: early release, response audio -> branch, manual cancel, unavailable service fallback. AI responses mocked.')
    finally:
        server.shutdown();server.server_close();thread.join()


if __name__=='__main__':main()
