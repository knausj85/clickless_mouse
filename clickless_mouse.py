# prototype of a clickless mouse mode using Talon. This does not coexist with the zoom, control mouse or mouse grid
# todo:
#  (1) smoother, accelerated scrolling
#  (2) horizontal scrolling
#  (3) detect non-clickless mouse events to dismiss
#  (4) better handling of mixed resolutions - 4k + non-4k etc
#  (5) Clicking some contexts menus (e.g. run as admin) in the start menu requires a double click???
from talon import Module, Context, app, ctrl, cron, settings
from .two_stage_clicker import two_stage_clicker
from .single_stage_clicker import single_stage_clicker
from .constants import *

import math, time



mod = Module()
ctx = Context()
mod.tag("clickless_mouse_enabled", desc="Indicates the clickless mouse is enabled")

clickless_method = mod.setting(
    "clickless_mouse_method",
    type=str,
    default="two_stage",
    desc="Either 'single_stage' or 'two_stage'",
)

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
        self.clicker = None

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
            self.clicker = self.create_clicker()
            self.x, self.y = ctrl.mouse_pos()
            self.update_cron = cron.interval("16ms", self.update)
        elif self.update_cron:
            cron.cancel(self.update_cron)
            self.update_cron = None
            self.state = STATE_MOUSE_IDLE
            self.clicker.on_disable()

    def create_clicker(self):
        match settings.get("user.clickless_mouse_method"):
            case "single_stage":
                clicker = single_stage_clicker()
            case _:
                clicker = two_stage_clicker()
        return clicker
    
    def toggle(self):
        self.enable(not self.enabled)

    def update(self):
        # print("update")
        x, y = ctrl.mouse_pos()
        now = time.perf_counter()
        update_last_xy = False
        # print("({},{})".format(x, y))
        if self.state == STATE_MOUSE_IDLE:
            # print("idle")
            if self.suppress_next_update:
                self.suppress_next_update = False
                update_last_xy = True
            elif math.fabs(self.x - x) > 1 or math.fabs(self.y - y) > 1:
                update_last_xy = True
                self.state = STATE_MOUSE_MOVING

        elif self.state == STATE_MOUSE_MOVING:
            # print("moving")

            if x == self.x and y == self.y:
                self.last_time = now
                self.state = STATE_MOUSE_STOPPED
            update_last_xy = True

        elif self.state == STATE_MOUSE_STOPPED:
            # print("stopped")

            if x == self.x and y == self.y:
                if now - self.last_time >= self.clicker.standstill_delay():
                    self.last_time = now
                    # self._dwell_x, self._dwell_y = ctrl.mouse_pos()
                    update_last_xy = True
                    self.state = self.clicker.on_standstill(self.x, self.y, self.is_left_down())
            else:
                update_last_xy = True
                self.state = STATE_MOUSE_MOVING
                self.clicker.on_movement_restart()
        elif self.state == STATE_DISPLAYING_OPTIONS:
            on_panel_display_result = self.clicker.on_panel_display(x, y)

            self.state = on_panel_display_result.next_state
            self.suppress_next_update = on_panel_display_result.suppress_next_update
            update_last_xy = on_panel_display_result.update_last_xy
            
        if update_last_xy:
            self.x, self.y = ctrl.mouse_pos()

cm = clickless_mouse()


@mod.action_class
class Actions:
    def clickless_mouse_toggle():
        """Toggles the click less mouse"""
        cm.toggle()

    def clickless_mouse_enable():
        """Enables the click less mouse"""
        cm.enable(True)

    def clickless_mouse_disable():
        """Disable the click less mouse"""
        cm.enable(False)
    
    def clickless_mouse_next_standstill_action(action: str):
        """With the single-stage method, this sets the next standstill action"""
        cm.clicker.set_next_standstill_action(action)

    def clickless_mouse_is_enabled():
        """Returns whether or not the click less mouse is enabled"""
        return cm.enabled
        


# uncomment the following for quick testing
# def on_ready():
#     cm.enable(True)


# app.register("ready", on_ready)
