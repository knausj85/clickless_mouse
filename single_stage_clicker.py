import time
from talon import Module, Context, app, ctrl, cron, actions, settings
from .clicker_base import clicker_base, on_panel_display_result
from .constants import *

class single_stage_clicker(clicker_base):
    def __init__(self):
        self.next_standstill_action = "left_click"
        self.action_mode = None

    def standstill_delay(self) -> int:
        return settings.get("user.clickless_mouse_dwell_time")

    def set_next_standstill_action(self, action):
        if action == "end_repeat":
            self.next_standstill_action = "left_click"
            self.action_mode = None
        else:
            self.next_standstill_action, self.action_mode, self.repeat_standstill_action = self.__parse_action__(action)

    def __parse_action__(self, action):
        list = action.split("+")
        next_standstill_action = list[0]
        action_mode = list[1] if len(list) > 1 else None
        repeat_standstill_action = next_standstill_action if action_mode == "repeat" else None
        return next_standstill_action, action_mode, repeat_standstill_action

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
                if self.action_mode == "repeat":
                    next_action = self.repeat_standstill_action


        self.next_standstill_action = next_action
        return STATE_MOUSE_IDLE, next_standstill_detection

    def on_movement_restart(self):
        pass
    
    # This will never be called as on_standstill never returns STATE_DISPLAYING_OPTIONS
    def on_panel_display(self, x, y):
        pass
