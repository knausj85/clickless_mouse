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
from .mouse_state_analyzer import mouse_state_analyzer
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
        self.state = STATE_MOUSE_IDLE
        self.enabled = False
        self.update_cron = None
        self.clicker = None
        self.mouse_state_analyzer = mouse_state_analyzer()

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
            self.mouse_state_analyzer.set_standstill_delay(self.clicker.standstill_delay())
            self.mouse_state_analyzer.set_standstill_detection(STANDSTILL_DETECT_ONLY_IF_MOUSE_BUTTONS_UP)
            self.mouse_state_analyzer.enable()
            self.update_cron = cron.interval("16ms", self.update)
            
        elif self.update_cron:
            cron.cancel(self.update_cron)
            self.update_cron = None
            self.clicker.on_disable()
        
        self.state = STATE_MOUSE_IDLE


    def create_clicker(self):
        method_name = settings.get("user.clickless_mouse_method")
        print("create clicker: ", method_name)
        match method_name:
            case "single_stage":
                clicker = single_stage_clicker()
            case "two_stage":
                clicker = two_stage_clicker()
            case _:
                if method_name != "":
                    print("invalid value for user.clickless_mouse_method:", method_name)
                clicker = two_stage_clicker()

        return clicker
    
    def toggle(self):
        self.enable(not self.enabled)

    def update(self):
        # print("update")
        analyzer = self.mouse_state_analyzer

        new_state = analyzer.determine_new_state()
        # if analyzer.state != new_state:
        #     print("previous:", analyzer.state, "new:", new_state)

        # perform actions when state changes
        if analyzer.state == STATE_MOUSE_STOPPED and new_state == STATE_MOUSE_MOVING:
            self.clicker.on_movement_restart()

        # perform actions whilst within specific states
        if new_state == STATE_MOUSE_STANDSTILL:
            # the clicker class's method tells us:
            # 1. what is our next state
            # 2. info to pass on to the mouse analyzer
            new_state, next_standstill_detection = self.clicker.on_standstill(analyzer.prev_x, analyzer.prev_y, self.is_left_down())
            self.mouse_state_analyzer.set_standstill_detection(next_standstill_detection)

        elif new_state == STATE_DISPLAYING_OPTIONS:
            x, y = ctrl.mouse_pos()
            display_result = self.clicker.on_panel_display(x, y)

            new_state = display_result.next_state
            analyzer.suppress_next_update = display_result.suppress_next_update
            if display_result.update_last_xy:
                analyzer.do_update_last_xy()

        analyzer.state = new_state

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
