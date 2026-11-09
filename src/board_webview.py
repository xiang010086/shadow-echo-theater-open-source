"""GTK4/WebKit6 desktop launcher for the supplied DshanPi Armbian image.

Uses the distribution's existing Python GI packages. --smoke exercises only
the local test cards; it is never enabled for a normal launch.
"""

import argparse
import json
from pathlib import Path
from board_buttons import BoardStartButton

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")
gi.require_version("WebKit", "6.0")
from gi.repository import Gdk, Gio, GLib, Gtk, WebKit  # noqa: E402


SMOKE_SCRIPT = r"""
(() => {
  window.boardSmoke = 'running';
  const delay = ms => new Promise(r => setTimeout(r, ms));
  async function waitFor(predicate, label) {
    const deadline = Date.now() + 120000;
    while (!predicate()) {
      const error = document.querySelector('#error');
      if (error && !error.hidden) throw new Error(error.textContent);
      if (Date.now() > deadline) throw new Error('timeout: ' + label);
      await delay(100);
    }
  }
  (async () => {
    await waitFor(() => !document.querySelector('#start').disabled, 'ready');
    for (const branch of ['hide', 'alone']) {
      document.querySelector('#start').click();
      await waitFor(() => !document.querySelector('#choices').hidden, 'choice');
      document.querySelector('#' + branch).click();
      await waitFor(() => document.querySelector('#stage').currentSrc.endsWith('/' + branch + '.mp4'), branch);
      await waitFor(() => document.querySelector('#status').textContent.includes('本轮完成'), 'ending');
      document.querySelector('#reset').click();
    }
    document.dispatchEvent(new KeyboardEvent('keydown', {key: 'g'}));
    await waitFor(() => document.querySelector('#stage').currentSrc.endsWith('/welcome.mp4'), 'welcome');
    await waitFor(() => !document.querySelector('#start').disabled, 'welcome return');
    window.boardSmoke = 'passed: both branches, shared ending, welcome';
  })().catch(error => { window.boardSmoke = 'FAILED: ' + error.message; });
  return 'smoke started';
})()
"""

STATUS_SCRIPT = r"""
JSON.stringify({
  status: document.querySelector('#status')?.textContent,
  error: document.querySelector('#error')?.hidden ? '' : document.querySelector('#error')?.textContent,
  source: document.querySelector('#stage')?.currentSrc,
  time: document.querySelector('#stage')?.currentTime,
  ready: document.querySelector('#stage')?.readyState,
  decodedFrames: document.querySelector('#stage')?.getVideoPlaybackQuality?.().totalVideoFrames,
  paused: document.querySelector('#stage')?.paused,
  muted: document.querySelector('#stage')?.muted,
  loop: document.querySelector('#stage')?.loop,
  videoWidth: document.querySelector('#stage')?.videoWidth,
  videoHeight: document.querySelector('#stage')?.videoHeight,
  smoke: window.boardSmoke || 'disabled'
})
"""


class StageApplication(Gtk.Application):
    def __init__(self, smoke=False, page=''):
        super().__init__(application_id="cn.yingyouhuisheng.StageTest",
                         flags=Gio.ApplicationFlags.NON_UNIQUE)
        self.smoke = smoke
        self.page = page
        self.started_smoke = False
        self.polling = False
        self.last_status = None
        self.snapshot_saved = False
        self.start_button = None
        self.connect("activate", self.activate_stage)
        self.connect("shutdown", self.close_buttons)

    def activate_stage(self, _application):
        window = Gtk.ApplicationWindow(application=self)
        window.set_title("影有回声 · 板端联调")
        window.set_default_size(1280, 720)
        policies=WebKit.WebsitePolicies(autoplay=WebKit.AutoplayPolicy.ALLOW)
        self.view = WebKit.WebView(network_session=WebKit.NetworkSession.new_ephemeral(),website_policies=policies)
        self.view.get_settings().set_media_playback_requires_user_gesture(False)
        self.view.connect("load-changed", self.on_load)
        self.view.connect("load-failed", self.on_load_failed)
        self.view.connect("web-process-terminated", self.on_process_terminated)
        window.set_child(self.view)
        controller = Gtk.EventControllerKey()
        controller.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)
        controller.connect('key-pressed', lambda _c, key, _code, _mods:
                           self.start_button is not None and self.start_button.keycode == 139 and key == Gdk.KEY_Menu)
        window.add_controller(controller)
        window.present()
        monitors = Gdk.Display.get_default().get_monitors()
        target = next((monitors.get_item(i) for i in range(monitors.get_n_items())
                       if (monitors.get_item(i).get_connector() or "").startswith("HDMI")), None)
        if target is not None:
            print("DISPLAY", target.get_connector(), flush=True)
            window.fullscreen_on_monitor(target)
        else:
            window.fullscreen()
        self.view.load_uri("http://127.0.0.1:8765/"+self.page)
        GLib.timeout_add_seconds(1, self.poll_status)
        if not self.smoke:
            try:
                config = json.loads((Path(__file__).resolve().parent/'public/config.json').read_text())
                code = config.get('boardStartKeycode')
                if type(code) is not int:
                    raise ValueError('Physical USER key not yet verified')
                self.start_button = BoardStartButton(code)
                GLib.timeout_add(50, self.poll_buttons)
                print('BOARD_START_BUTTON_READY adc-keys code='+str(code), flush=True)
            except (OSError, ValueError) as error:
                print('BOARD_START_BUTTON_UNAVAILABLE', str(error), flush=True)

    def poll_buttons(self):
        try:
            if self.start_button.read_pressed():
                print('BOARD_START_BUTTON_PRESSED code='+str(self.start_button.keycode), flush=True)
                self.view.evaluate_javascript("document.querySelector('#start')?.click()", -1,
                                              None, None, None, self.script_finished, None)
        except OSError as error:
            print('BOARD_START_BUTTON_FAILED', str(error), flush=True)
            self.close_buttons()
            return GLib.SOURCE_REMOVE
        return GLib.SOURCE_CONTINUE

    def close_buttons(self, *_args):
        if self.start_button is not None:
            self.start_button.close()
            self.start_button = None

    def on_load_failed(self, _view, _event, uri, error):
        print("LOAD_FAILED", uri, error.message, flush=True)
        return False

    def on_process_terminated(self, _view, reason):
        print("WEB_PROCESS_TERMINATED", reason, flush=True)
        self.quit()

    def on_load(self, _view, event):
        if event == WebKit.LoadEvent.FINISHED:
            print("PAGE_LOADED", flush=True)
            if self.smoke and not self.started_smoke:
                self.started_smoke = True
                self.view.evaluate_javascript(SMOKE_SCRIPT, -1, None, None,
                                              None, self.script_finished, None)

    def script_finished(self, view, result, _data):
        try:
            value = view.evaluate_javascript_finish(result)
            print("SCRIPT", value.to_string(), flush=True)
        except GLib.Error as error:
            print("SCRIPT_FAILED", error.message, flush=True)

    def poll_status(self):
        control=Path(__file__).resolve().parent/'.run/board-control.json'
        if control.is_file():
            try:
                if control.stat().st_size>512:raise ValueError('Control file too large')
                action=json.loads(control.read_text()).get('action')
                scripts={
                    'start':"document.querySelector('#start')?.click()",
                    'reset':"clearInterval(window.micCheckTimer);document.querySelector('#mic-check-overlay')?.remove();document.querySelector('#reset')?.click()",
                    'skip-current':"(()=>{const v=document.querySelector('#stage');if(v&&!v.loop&&Number.isFinite(v.duration))v.currentTime=Math.max(0,v.duration-.08)})()",
                    'mic-prepare':"(()=>{document.querySelector('#stage')?.pause();document.querySelector('#mic-check-overlay')?.remove();const d=document.createElement('div');d.id='mic-check-overlay';d.setAttribute('role','status');d.style.cssText='position:fixed;inset:0;z-index:9999;display:grid;place-content:center;white-space:pre-line;text-align:center;background:#100e0c;color:#ffe7b6;font:48px sans-serif;line-height:1.8';d.textContent='收音检查\\n等待开始，先不用说话';document.body.append(d)})()",
                    'mic-countdown':"(()=>{const d=document.querySelector('#mic-check-overlay');if(!d)return;clearInterval(window.micCheckTimer);let n=10;const tick=()=>{d.textContent=n>0?'收音检查\\n'+n+'\\n请等倒计时结束再说话':'马上开始收音';if(n--<=0)clearInterval(window.micCheckTimer)};tick();window.micCheckTimer=setInterval(tick,1000)})()",
                    'mic-recording':"clearInterval(window.micCheckTimer);(()=>{const d=document.querySelector('#mic-check-overlay');if(d)d.textContent='正在收音\\n现在请说一句完整的话\\n还有10秒'})()",
                    'mic-finished':"clearInterval(window.micCheckTimer);(()=>{const d=document.querySelector('#mic-check-overlay');if(d)d.textContent='录音结束\\n正在检查，先不用继续说话'})()",
                }
                control.unlink()
                if action=='snapshot':self.snapshot_saved=False
                elif action in scripts:self.view.evaluate_javascript(scripts[action],-1,None,None,None,self.script_finished,None)
            except (OSError,ValueError,AttributeError) as error:
                print('CONTROL_FAILED',type(error).__name__,flush=True)
        if not self.polling:
            self.polling = True
            self.view.evaluate_javascript(STATUS_SCRIPT, -1, None, None,
                                          None, self.status_finished, None)
        return GLib.SOURCE_CONTINUE

    def status_finished(self, view, result, _data):
        self.polling = False
        try:
            status = json.loads(view.evaluate_javascript_finish(result).to_string())
            key = (status.get("status"), status.get("error"), status.get("smoke"),
                   status.get('source'), status.get('paused'), int(status.get('time') or 0)//10)
            if key != self.last_status:
                self.last_status = key
                print("STATUS", json.dumps(status, ensure_ascii=False), flush=True)
            if (status.get("ready", 0) >= 3 and status.get("time", 0) > (4 if self.page else .25)
                    and not self.snapshot_saved):
                self.snapshot_saved = True
                view.get_snapshot(WebKit.SnapshotRegion.VISIBLE,
                                  WebKit.SnapshotOptions.NONE, None,
                                  self.snapshot_finished, None)
        except (GLib.Error, ValueError, AttributeError) as error:
            print("STATUS_FAILED", str(error), flush=True)

    def snapshot_finished(self, view, result, _data):
        try:
            texture = view.get_snapshot_finish(result)
            target = Path(__file__).resolve().parent / "logs" / "board-screen.png"
            target.parent.mkdir(exist_ok=True)
            if not texture.save_to_png(str(target)):
                raise OSError("PNG save returned false")
            print("SNAPSHOT", str(target), flush=True)
        except (GLib.Error, OSError) as error:
            print("SNAPSHOT_FAILED", str(error), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--smoke", action="store_true")
    parser.add_argument('--page', choices=['','lure/index.html'], default='')
    options = parser.parse_args()
    raise SystemExit(StageApplication(smoke=options.smoke,page=options.page).run([]))
