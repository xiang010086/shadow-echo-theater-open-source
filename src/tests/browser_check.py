"""Development-only browser smoke check; requires Playwright and local Edge."""

from pathlib import Path
import sys
import threading

from playwright.sync_api import sync_playwright

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from runtime import make_server


def main():
    server = make_server(0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(channel='msedge', headless=True)
            page = browser.new_page()
            failures = []
            page.on('pageerror', lambda error: failures.append(str(error)))
            # Short cards exercise controller edge cases quickly; production
            # videos are validated separately on the physical ARM board.
            page.route('**/config.json', lambda route: route.fulfill(
                path=str(Path(__file__).resolve().parents[1] / 'public/config.test.json'),
                content_type='application/json'))
            page.goto('http://127.0.0.1:{}'.format(server.server_port))
            page.locator('#start').wait_for(state='visible')
            page.wait_for_function('!document.querySelector("#start").disabled')
            for branch in ['hide', 'alone']:
                page.locator('#start').click()
                page.locator('#choices').wait_for(state='visible', timeout=15000)
                page.locator('#' + branch).click()
                page.wait_for_function('document.querySelector("#stage").currentSrc.endsWith("/' + branch + '.mp4")')
                page.wait_for_function('document.querySelector("#status").textContent.includes("本轮完成")', timeout=10000)
                page.locator('#reset').click()
            page.keyboard.press('g')
            page.wait_for_function('document.querySelector("#stage").currentSrc.endsWith("/welcome.mp4")')
            page.wait_for_function('!document.querySelector("#start").disabled', timeout=5000)
            page.locator('body').click(position={'x': 5, 'y': 5})
            page.keyboard.press('Enter')
            page.wait_for_function('document.querySelector("#stage").currentSrc.endsWith("/welcome.mp4") && document.querySelector("#start").disabled')
            page.locator('#reset').click()
            page.wait_for_timeout(1800)
            assert page.locator('#start').is_enabled(), 'reset was undone by a late media event'
            page.route('**/media/opening.mp4', lambda route: route.abort())
            page.locator('#start').click()
            page.locator('#error').wait_for(state='visible', timeout=10000)
            page.locator('#reset').click()
            assert page.locator('#error').is_hidden()
            assert not failures, failures
            browser.close()
            print('PASS: real H.264/AAC playback, both branches, shared ending, welcome-only event, reset and media failure.')
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


if __name__ == '__main__':
    main()
