import re
import bot.states as states
from . import detector
from . import input

from PIL import Image
from time import sleep
import win32gui

class Bot:


    op_map = {
        '<': lambda a, b: a < b,
        '<=': lambda a, b: a <= b,
        '>': lambda a, b: a > b,
        '>=': lambda a, b: a >= b,
    }


    def __init__(self, cfg):
        self.cfg = cfg
        print ('find window %s' % cfg['window_title'])
        self.hwnd = win32gui.FindWindow(None, cfg['window_title'])
        print('hwnd %d' % self.hwnd)
        detector.init_tesseract(cfg.get('tesseract_path'))
        self.current_state = None
        self.ship_status = {}
        self.status_pattern = re.compile('\s*(\d+)/(\d+).*')
        self.condition_pattern = re.compile('(\w+)(\W+)(\d+)')


    def run(self):
        frame_interval = self.cfg.get('frame_interval', float)

        self.change_state(states.FindEnemy)
        while True:
            sleep(frame_interval)
            self.refresh_screen()
            self.current_state.update()


    def change_state(self, cls):
        if self.current_state is not None:
            self.current_state.exit()
        self.current_state = cls(self)
        self.current_state.enter()
        

    def refresh_screen(self):
        self.screen = detector.capture_window(self.hwnd)


    def refresh_ship_status(self):
        pos = self.cfg['status_bar_pos']
        input.mouse_click_left(self.hwnd, pos[0], pos[1], 1)
        self.screen = detector.capture_window(self.hwnd)
        self.click_blank()
        self.read_ship_status()


    def check_enemy(self):
        img = detector.get_template('check_enemy')
        rect = tuple(self.cfg['overview_summery_rect'])
        overview_summery = self.screen.crop(rect)
        pos = detector.locate_image(overview_summery, img, 0.6)
        return pos is not None


    # overview_type = (enemy, mine, spot, station, fortress)
    def switch_overview(self, overview_type):
        self.click_blank()
        img = detector.get_template('overview_' + overview_type)
        rect = tuple(self.cfg['overview_types_rect'])
        overview = self.screen.crop(rect)
        pos = detector.locate_image(overview, img, 0.6)
        if pos is not None:
            input.mouse_click_left(self.hwnd, pos[0] + rect[0], pos[1] + rect[1])
            sleep(self.cfg.get('ui_sleep_time', float) * 2)
            return True
        return False


    def read_overview_items(self):
        item_offset = self.cfg['overview_items_offset_y']
        overview_rect = tuple(self.cfg['overview_items_rect'])
        screen = self.screen
        items = []
        for i in range(5):
            rect = (overview_rect[0], overview_rect[1] + item_offset * i, overview_rect[2], overview_rect[1] + item_offset * (i + 1))
            txt = detector.read_image_text(screen, rect)
            print(txt)
            items.append((txt, ((rect[0] + rect[2]) / 2, (rect[1] + rect[3]) / 2)))
        return items


    def check_equip_button(self, idx):
        button = self.screen.crop(self.get_equip_button_rect(idx))
        # button.save("btn%d.png" % idx)
        img = detector.get_template('check_equip_active')
        pos = detector.locate_image(button, img, 0.95)
        return pos is not None


    def get_equip_button_rect(self, idx):
        rect = tuple(self.cfg['equipments']['rect'])
        w = (rect[2] - rect[0]) / 6
        h = (rect[3] - rect[1]) / 2
        r = int(idx / 6)
        c = idx % 6
        x = rect[0] + c * w
        y = rect[1] + r * h
        return (x, y, x + w, y + h)


    def get_equip_button_position(self, idx):
        rect = self.get_equip_button_rect(idx)
        return ((rect[0] + rect[2]) / 2, (rect[1] + rect[3]) / 2 )


    def read_ship_status(self):
        screen = self.screen
        status_rects = self.cfg["status_rects"]
        for key, rect in status_rects.items():
            txt = detector.read_image_text(screen, rect)
            txt = txt.replace(',', '')
            txt = txt.replace('.', '')
            match = self.status_pattern.match(txt)
            if match is not None:
                self.ship_status[key] = (float(match.group(1)) / float(match.group(2))) * 100
        print(self.ship_status)


    def check_condition(self, condition):
        if isinstance(condition, str):
            match = self.condition_pattern.match(condition)
            if match is None:
                return False
            (key, op, value) = match.groups()
            print(match.groups())
            op = self.op_map.get(op)
            if op is not None:
                return op(self.ship_status.get(key, 0), float(value))
        return bool(condition)


    def click_blank(self):
        input.mouse_click_left(self.hwnd, 10, 600)