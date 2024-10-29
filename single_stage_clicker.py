import time
from talon import Module, Context, app, ctrl, cron, actions, settings
from .clicker_base import clicker_base, on_panel_display_result
from .constants import *

class single_stage_clicker(clicker_base):
    def __init__(self):
        self.next_standstill_action = "left_click"
        pass

    def standstill_delay(self) -> int:
        return settings.get("user.clickless_mouse_dwell_time")

    def set_next_standstill_action(self, action):
        self.next_standstill_action = action
        pass

    def on_disable(self):
        pass

    def on_standstill(self, x, y, is_left_down) -> int:
        match self.next_standstill_action:
            case "left_click":
                ctrl.mouse_click(button=left_mouse_button_index)
            case "right_click":
                ctrl.mouse_click(button=right_mouse_button_index)

        self.next_standstill_action = "left_click"
        return STATE_MOUSE_IDLE

    def on_movement_restart(self):
        pass
    
    # This will never be called as on_standstill never returns STATE_DISPLAYING_OPTIONS
    def on_panel_display(self, x, y):
        pass
