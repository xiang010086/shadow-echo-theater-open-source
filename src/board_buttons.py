"""Read only the board's ADC user keys; MENU starts an idle show."""
import os
import struct
import time
from pathlib import Path

EVENT = struct.Struct('=qqHHi')  # Linux ARM64 input_event, 24 bytes.
ADC_DEVICE = Path('/dev/input/by-path/platform-adc-keys-event')


class MenuPressDecoder:
    def __init__(self, keycode=139):
        if keycode not in {114, 115, 139, 158}:
            raise ValueError('Expected a verified ADC user-key code')
        self.keycode = keycode
        self.buffer = b''
        self.down = False
        self.last_press = float('-inf')

    def feed(self, data, now=None):
        now = time.monotonic() if now is None else now
        self.buffer += data
        presses = 0
        while len(self.buffer) >= EVENT.size:
            _, _, kind, code, value = EVENT.unpack(self.buffer[:EVENT.size])
            self.buffer = self.buffer[EVENT.size:]
            if kind != 1 or code != self.keycode:
                continue
            if value == 0:
                self.down = False
            elif value == 1 and not self.down:
                self.down = True
                if now - self.last_press >= .6:
                    presses += 1
                    self.last_press = now
        return presses


class BoardStartButton:
    def __init__(self, keycode):
        name = Path('/sys/class/input') / ADC_DEVICE.resolve(strict=True).name / 'device/name'
        if name.read_text().strip() != 'adc-keys':
            raise OSError('Expected ADC user-key device')
        self.decoder = MenuPressDecoder(keycode)
        self.keycode = keycode
        self.fd = os.open(ADC_DEVICE, os.O_RDONLY | os.O_NONBLOCK)

    def read_pressed(self):
        try:
            data = os.read(self.fd, EVENT.size * 32)
        except BlockingIOError:
            return 0
        if not data:
            raise OSError('ADC input device disconnected')
        return self.decoder.feed(data)

    def close(self):
        if self.fd is not None:
            os.close(self.fd)
            self.fd = None
