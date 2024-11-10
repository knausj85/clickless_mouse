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

    def on_standstill(self, x, y, is_left_down) -> tuple[int, int]:
        next_action = "left_click"
        next_standstill_detection = STANDSTILL_DETECT_ONLY_IF_MOUSE_BUTTONS_UP
        match self.next_standstill_action:
            case "left_click":
                ctrl.mouse_click(button=left_mouse_button_index)
            case "left_dubclick":
                ctrl.mouse_click(button=left_mouse_button_index)
                ctrl.mouse_click(button=left_mouse_button_index)
            case "right_click":
                ctrl.mouse_click(button=right_mouse_button_index)
            case "left_drag":
                actions.user.mouse_drag(0)
                next_action = "end_drag"
                next_standstill_detection = STANDSTILL_DETECT_ALWAYS
            case "end_drag":
                actions.user.mouse_drag_end()

        self.next_standstill_action = next_action

        return STATE_MOUSE_IDLE, next_standstill_detection

    def on_movement_restart(self):
        pass
    
    # This will never be called as on_standstill never returns STATE_DISPLAYING_OPTIONS
    def on_panel_display(self, x, y):
        pass
