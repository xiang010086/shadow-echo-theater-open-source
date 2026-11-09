import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from board_buttons import EVENT, MenuPressDecoder


def event(code=139, value=1, kind=1):
    return EVENT.pack(0, 0, kind, code, value)


class BoardButtonTests(unittest.TestCase):
    def test_only_the_physically_verified_code_is_used(self):
        decoder = MenuPressDecoder(keycode=158)
        self.assertEqual(decoder.feed(event(139), now=1), 0)
        self.assertEqual(decoder.feed(event(158), now=1), 1)
        with self.assertRaises(ValueError):
            MenuPressDecoder(keycode=116)

    def test_menu_press_is_one_action_not_hold_repeats(self):
        decoder = MenuPressDecoder()
        self.assertEqual(decoder.feed(event(), now=1), 1)
        self.assertEqual(decoder.feed(event(value=2) + event(), now=2), 0)
        self.assertEqual(decoder.feed(event(value=0) + event(), now=3), 1)

    def test_other_board_keys_cannot_start_a_show(self):
        decoder = MenuPressDecoder()
        for code in [114, 115, 116, 158]:
            self.assertEqual(decoder.feed(event(code), now=1), 0)
        self.assertEqual(decoder.feed(event(kind=0), now=1), 0)

    def test_partial_input_events_are_buffered(self):
        decoder = MenuPressDecoder()
        payload = event()
        self.assertEqual(decoder.feed(payload[:9], now=1), 0)
        self.assertEqual(decoder.feed(payload[9:], now=1), 1)

    def test_switch_bounce_cannot_double_start(self):
        decoder = MenuPressDecoder()
        self.assertEqual(decoder.feed(event(), now=1), 1)
        self.assertEqual(decoder.feed(event(value=0) + event(), now=1.1), 0)


if __name__ == '__main__':
    unittest.main()
