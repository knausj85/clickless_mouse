import time
from talon import Module, Context, app, ctrl, cron, actions, settings
from .clicker_base import clicker_base, on_panel_display_result
from .constants import *

class two_stage_clicker(clicker_base):
    def __init__(self, dwell_panel):
        self.dwell_panel = dwell_panel
        self._dwell_x = self._dwell_y = None
        self.crosshair_x = self.crosshair_y = None

    def on_disable(self):
        self.dwell_panel.unregister_and_close_canvas()

    def on_standstill(self, x, y, is_left_down) -> int:
        self._dwell_x, self._dwell_y = x, y
        self.crosshair_x, self.crosshair_y = x, y
        self.dwell_panel.create_panel(x, y, is_left_down)
        return STATE_DISPLAYING_OPTIONS

    def on_movement_restart(self):
        self.dwell_panel.clear_button_positions()
    
    def on_panel_display(self, x, y) -> on_panel_display_result:
        # print("display")
        now = time.perf_counter()
        item_hit = self.dwell_panel.find_hit(x, y, now)
        self.draw_options = True
        self.next_state = STATE_DISPLAYING_OPTIONS
        self.update_last_xy = False
        self.suppress_next_update = False

        if (
            settings.get("user.clickless_mouse_auto_hide") >= 1
            and not item_hit
            and now - self.last_time >= settings.get("user.clickless_mouse_auto_hide_time")
            and (self._dwell_x == x or self._dwell_y == y)
        ):
            # update the position to prevent re-display for minor moves within the bounds
            # this may not be preferred.
            if settings.get("user.clickless_mouse_prevent_redisplay_for_minor_motions") >= 1:
                self.update_last_xy = True

            self.next_state = STATE_MOUSE_IDLE

            self.draw_options = False

        elif item_hit and now - item_hit.last_hit_time >= settings.get("user.clickless_mouse_dwell_time"):
            self.handle_action(item_hit, self.crosshair_x, self.crosshair_y)

        elif self.dwell_panel.is_outside_panel(x, y):
            self.draw_options = False
            self.next_state = STATE_MOUSE_IDLE

        if self.draw_options:
            if self._dwell_x != x or self._dwell_y != y:
                self.last_time = now
                self._dwell_x, self._dwell_y = ctrl.mouse_pos()

            if not self.dwell_panel.draw_registered:
                self.dwell_panel.register_canvas()
        else:
            self.dwell_panel.unregister_canvas()

        return on_panel_display_result(self.next_state, self.update_last_xy, self.suppress_next_update)

    def handle_action(self, item_hit, x, y) -> None:
        self.draw_options = False
        self.suppress_next_update = False

        # print("performing action...")
        action = item_hit.action
        if (
            action != "su"
            and action != "sd"
            and action != "ka"
            and action != "x"
        ):
            self.suppress_next_update = True
            ctrl.mouse_move(x, y)

        if item_hit.action == "lh":
            # print("left hold")
            if not self.is_left_down():
                # print("pressing button 0 down")
                ctrl.mouse_click(button=left_mouse_button_index, down=True)
            else:
                # print("pressing button 0 up")
                actions.sleep("{}ms".format(settings.get("user.clickless_mouse_release_delay")))
                ctrl.mouse_click(button=left_mouse_button_index, up=True)

            # print(str(ctrl.mouse_buttons_down()))
        elif item_hit.action == "lr":
            if self.is_left_down():
                actions.sleep("{}ms".format(settings.get("user.clickless_mouse_release_delay")))
                ctrl.mouse_click(button=left_mouse_button_index, up=True)

        elif item_hit.action == "l":
            ctrl.mouse_click(button=left_mouse_button_index)

        elif item_hit.action == "ld":
            ctrl.mouse_click(button=left_mouse_button_index)
            ctrl.mouse_click(button=left_mouse_button_index)

        elif item_hit.action == "lt":
            ctrl.mouse_click(button=left_mouse_button_index)
            ctrl.mouse_click(button=left_mouse_button_index)
            ctrl.mouse_click(button=left_mouse_button_index)

        elif item_hit.action == "r":
            ctrl.mouse_click(button=right_mouse_button_index)

        elif item_hit.action == "rh":
            if right_mouse_button_index not in ctrl.mouse_buttons_down():
                ctrl.mouse_click(button=right_mouse_button_index, down=True)
            else:
                actions.sleep("{}ms".format(settings.get("user.clickless_mouse_release_delay")))
                ctrl.mouse_click(button=right_mouse_button_index, up=True)
        elif item_hit.action == "su":
            actions.mouse_scroll(y=-10)
            self.draw_options = True

        elif item_hit.action == "sd":
            actions.mouse_scroll(y=10)
            self.draw_options = True
        elif item_hit.action == "ka":
            self.draw_options = True
        elif item_hit.action == "x":
            self.draw_options = False
            self.update_last_xy = True
            self.next_state = STATE_MOUSE_IDLE

        if action != "su" and action != "sd" and action != "ka":
            # print("({},{})".format(self.x, self.y))
            self.update_last_xy = True
            # print("({},{})".format(self.x, self.y))
            self.next_state = STATE_MOUSE_IDLE

