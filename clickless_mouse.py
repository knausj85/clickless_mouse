# prototype of a clickless mouse mode using Talon. This does not coexist with the zoom, control mouse or mouse grid
# todo:
#  (1) smoother, accelerated scrolling
#  (2) horizontal scrolling
#  (3) detect non-clickless mouse events to dismiss
#  (4) better handling of mixed resolutions - 4k + non-4k etc
#  (5) Clicking some contexts menus (e.g. run as admin) in the start menu requires a double click???
from talon import Module, Context, app, ctrl, cron, actions, settings
from .dwell_panel import dwell_panel

import math, time

left_mouse_button_index = 0
right_mouse_button_index = 1


mod = Module()
ctx = Context()
mod.tag("clickless_mouse_enabled", desc="Indicates the clickless mouse is enabled")

STATE_MOUSE_IDLE = 0
STATE_MOUSE_MOVING = 1
STATE_MOUSE_STOPPED = 2
STATE_DISPLAYING_OPTIONS = 3

dwell_time = mod.setting(
    "clickless_mouse_dwell_time",
    type=float,
    default=0.250,
    desc="The required dwell time before triggering the action",
)

auto_hide = mod.setting(
    "clickless_mouse_auto_hide",
    type=int,
    default=1,
    desc="toggles the functionality to auto hide within the bounds",
)

auto_hide_time = mod.setting(
    "clickless_mouse_auto_hide_time",
    type=float,
    default=1.25,
    desc="The time before the clickless mouse is auto-hidden",
)

mouse_idle = mod.setting(
    "clickless_mouse_idle_time_before_display",
    type=float,
    default=0.35,
    desc="The time the mouse must be idle before the clickless mouse options are displayed",
)

radius = mod.setting(
    "clickless_mouse_radius",
    type=int,
    default=15 if app.platform == "mac" else 20,
    desc="The size of the options in the clickless mouse",
)

release_button_delay = mod.setting(
    "clickless_mouse_release_delay",
    type=int,
    default=50,
    desc="The delay (ms) before releasing the held mouse button",
)


prevent_redisplay_for_minor_motions = mod.setting(
    "clickless_mouse_prevent_redisplay_for_minor_motions",
    type=int,
    default=0,
    desc="A value of 1 or more prevents re-display for minor motions",
)

vertical_offset = mod.setting(
    "clickless_mouse_vertical_offset",
    type=float,
    default=2.25,
    desc="when drawing the options horizontally, this determines the vertical distance from the mouse. The total distance is the value times the radius.",
)

horizontal_offset = mod.setting(
    "clickless_mouse_horizontal_offset",
    type=float,
    default=2.25,
    desc="when drawing the options horizontally, this determines the distance between the options. The total distance is the value times the radius.",
)

stroke_width = mod.setting(
    "clickless_mouse_stroke_width",
    type=int,
    default=3,
    desc="The width the stroke for the cursor position.",
)


class clickless_mouse:
    def __init__(self):
        self.x, self.y = ctrl.mouse_pos()
        self._dwell_x, self._dwell_y = ctrl.mouse_pos()
        self.state = STATE_MOUSE_IDLE
        self.last_time = 0
        self.enabled = False
        self.update_cron = None
        self.dwell_panel = dwell_panel()

        # after moving the mouse to perform an action,
        # avoid a state change in the first update.
        # this prevents an unnecessary re-display
        self.suppress_next_update = False

    def is_left_down(self):
        return left_mouse_button_index in ctrl.mouse_buttons_down()

    def enable(self, _enable):
        if _enable == self.enabled:
            return

        self.enabled = _enable

        if self.enabled:
            ctx.tags = ["user.clickless_mouse_enabled"]
        else:
            ctx.tags = []

        if self.enabled:
            self.x, self.y = ctrl.mouse_pos()
            self.update_cron = cron.interval("16ms", self.update)
        elif self.update_cron:
            cron.cancel(self.update_cron)
            self.update_cron = None
            self.state = STATE_MOUSE_IDLE
            self.dwell_panel.unregister_and_close_canvas()

    def toggle(self):
        self.enable(not self.enabled)

    def update(self):
        # print("update")
        x, y = ctrl.mouse_pos()
        now = time.perf_counter()
        # print("({},{})".format(x, y))
        if self.state == STATE_MOUSE_IDLE:
            # print("idle")
            if self.suppress_next_update:
                self.suppress_next_update = False
                self.x, self.y = ctrl.mouse_pos()
                return
            elif math.fabs(self.x - x) > 1 or math.fabs(self.y - y) > 1:
                self.x, self.y = ctrl.mouse_pos()
                self.state = STATE_MOUSE_MOVING

        elif self.state == STATE_MOUSE_MOVING:
            # print("moving")

            if x == self.x and y == self.y:
                self.x, self.y = ctrl.mouse_pos()
                self.last_time = now
                self.state = STATE_MOUSE_STOPPED
            else:
                self.x, self.y = ctrl.mouse_pos()

        elif self.state == STATE_MOUSE_STOPPED:
            # print("stopped")

            if x == self.x and y == self.y:
                if now - self.last_time >= settings.get("user.clickless_mouse_auto_hide_time"):
                    self.last_time = now
                    self._dwell_x, self._dwell_y = ctrl.mouse_pos()
                    self.x, self.y = ctrl.mouse_pos()
                    self.dwell_panel.create_panel(self.x, self.y, self.is_left_down())

                    self.state = STATE_DISPLAYING_OPTIONS
            else:
                self.x, self.y = ctrl.mouse_pos()
                self.state = STATE_MOUSE_MOVING
                self.dwell_panel.clear_button_positions()
        elif self.state == STATE_DISPLAYING_OPTIONS:
            # print("display")
            draw_options = True
            item_hit = self.dwell_panel.find_hit(x, y, now)

            if (
                settings.get("user.clickless_mouse_auto_hide") >= 1
                and not item_hit
                and now - self.last_time >= settings.get("user.clickless_mouse_auto_hide_time")
                and (self._dwell_x == x or self._dwell_y == y)
            ):
                # update the position to prevent re-display for minor moves within the bounds
                # this may not be preferred.
                if settings.get("user.clickless_mouse_prevent_redisplay_for_minor_motions") >= 1:
                    self.x, self.y = ctrl.mouse_pos()

                self.state = STATE_MOUSE_IDLE

                draw_options = False

            elif item_hit and now - item_hit.last_hit_time >= settings.get("user.clickless_mouse_dwell_time"):
                draw_options = self.handle_action(item_hit)

            elif self.dwell_panel.is_outside_panel(x, y):
                draw_options = False
                self.state = STATE_MOUSE_IDLE

            if draw_options:
                if self._dwell_x != x or self._dwell_y != y:
                    self.last_time = now
                    self._dwell_x, self._dwell_y = ctrl.mouse_pos()

                if not self.dwell_panel.draw_registered:
                    self.dwell_panel.register_canvas()
            else:
                self.dwell_panel.unregister_canvas()

    def handle_action(self, item_hit):

        # print("performing action...")
        action = item_hit.action
        if (
            action != "su"
            and action != "sd"
            and action != "ka"
            and action != "x"
        ):
            self.suppress_next_update = True
            ctrl.mouse_move(self.x, self.y)

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
            draw_options = True

        elif item_hit.action == "sd":
            actions.mouse_scroll(y=10)
            draw_options = True
        elif item_hit.action == "ka":
            draw_options = True
        elif item_hit.action == "x":
            draw_options = False
            self.x, self.y = ctrl.mouse_pos()
            self.state = STATE_MOUSE_IDLE

        if action != "su" and action != "sd" and action != "ka":
            # print("({},{})".format(self.x, self.y))
            self.x, self.y = ctrl.mouse_pos()
            # print("({},{})".format(self.x, self.y))
            self.state = STATE_MOUSE_IDLE

cm = clickless_mouse()


@mod.action_class
class Actions:
    def clickless_mouse_toggle():
        """Toggles the click less mouse"""
        cm.toggle()

    def clickless_mouse_enable():
        """Toggles the click less mouse"""
        cm.enable(True)

    def clickless_mouse_disable():
        """Toggles the click less mouse"""
        cm.enable(False)
    
    def clickless_mouse_is_enabled():
        """Returns whether or not the click less mouse is enabled"""
        return cm.enabled
        


# uncomment the following for quick testing
# def on_ready():
#     cm.enable(True)


# app.register("ready", on_ready)
