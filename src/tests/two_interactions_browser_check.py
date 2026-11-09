"""Both real browser interaction stops; audio/AI results explicitly mocked."""
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
    server=make_server(0);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    public=Path(__file__).resolve().parents[1]/'public'
    config=json.loads((public/'config.test.json').read_text(encoding='utf-8'))
    config.update(twoInteractions=True,testMedia=False)
    config['clips']['prediction']=config['clips']['question']
    data=io.BytesIO()
    with wave.open(data,'wb') as output:
        output.setnchannels(1);output.setsampwidth(2);output.setframerate(16000);output.writeframes(bytes(3200))
    context={'interaction':'method','phase':'idle'};starts=[];errors=[]
    try:
        with sync_playwright() as p:
            browser=p.chromium.launch(channel='msedge',headless=True)
            page=browser.new_page(viewport={'width':1280,'height':720})
            page.on('pageerror',lambda error:errors.append(str(error)))
            page.route('**/config.json',lambda route:route.fulfill(json=config))
            page.route('**/media/runtime-voice/*.wav',lambda route:route.fulfill(body=data.getvalue(),content_type='audio/wav'))
            def api(route):
                action=route.request.url.rsplit('/',1)[-1]
                if action=='start':
                    context.update(interaction=route.request.post_data_json['interaction'],phase='recording')
                    starts.append(context['interaction'])
                if action=='stop':context['phase']='done'
                if action=='cancel':context['phase']='idle'
                result=dict(phase=context['phase'],ready=True)
                if context['phase']=='done':
                    result.update(branch='tiger' if context['interaction']=='prediction' else 'alone',
                                  response='咱们接着验一验！',audio='media/runtime-voice/'+'b'*32+'.wav')
                route.fulfill(json=result)
            page.route('**/api/voice/*',api)
            page.goto(f'http://127.0.0.1:{server.server_port}')
            page.wait_for_function('!document.querySelector("#start").disabled')
            page.keyboard.press('Enter')
            for label in ('猜狐狸','藏好观察'):
                page.wait_for_function('(label)=>!document.querySelector("#choices").hidden && document.querySelector("#hide").textContent.includes(label)',arg=label,timeout=20000)
                assert page.locator('body').inner_text()==''
                box=page.locator('#stage').bounding_box();assert box['height']==720 and box['width']==1280
                page.keyboard.down('Space');page.wait_for_timeout(250);page.keyboard.up('Space')
            page.wait_for_function('document.querySelector("#status").textContent.includes("本轮完成")',timeout=15000)
            assert starts==['prediction','method'],starts
            assert not errors,errors
            browser.close()
            print('PASS: two voice contexts, full viewport, no visible text, shared ending. ASR and AI mocked.')
    finally:
        server.shutdown();server.server_close();thread.join()


if __name__=='__main__':main()
