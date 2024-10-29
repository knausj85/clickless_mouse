import time
from talon import Module, Context, app, ctrl, cron, actions, settings
from .clicker_base import clicker_base, on_panel_display_result
from .constants import *

class single_stage_clicker(clicker_base):
    def __init__(self):
        # self.crosshair_x = self.crosshair_y = None
        pass

    def standstill_delay(self) -> int:
        return settings.get("user.clickless_mouse_dwell_time")

    def on_disable(self):
        # self.dwell_panel.unregister_and_close_canvas()
        pass

    def on_standstill(self, x, y, is_left_down) -> int:
        ctrl.mouse_click(button=left_mouse_button_index)
        return STATE_MOUSE_IDLE

    def on_movement_restart(self):
        pass
    
    def on_panel_display(self, x, y) -> on_panel_display_result:
        pass
