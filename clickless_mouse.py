# prototype of a clickless mouse mode using Talon. This does not coexist with the zoom, control mouse or mouse grid
# todo:
#  (1) smoother, accelerated scrolling
#  (2) horizontal scrolling
#  (3) cleanup and simplify bounds around displayed options
#  (4) detect non-clickless mouse events to dismiss
#  (5) decide if the circular case 9 is worth keeping
#  (6) better handling of mixed resolutions - 4k + non-4k etc
#  (7) consolidate cases? many are redundant now if we simply draw horizontally
from talon import Module, Context, app, canvas, screen, ui, ctrl, cron, actions

import math, time

# l = left click
# lh = left hold
# lr = left release. when left is down, all options become lr
# ld = left double click
# su = scroll up
# sd = scroll down
# r = right click
# rh = right click old, DISABLED, doesn't work yet.
# ka = keep alive for e.g. leaving the thing up for easy scroll down/up on webpages. no action
horizontal_button_order = ["l", "ld", "lt", "lh", "r", "su", "sd", "ka"]
left_mouse_button_index = 0
right_mouse_button_index = 1


mod = Module()
ctx = Context()
mod.mode("clickless_mouse_enabled", desc="Indicates the clickless mouse is enabled")

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


class dwell_button:
    def __init__(self, x, y, action="l"):
        self.x = x
        self.y = y
        self.hit = False
        self.action = action
        self.last_hit_time = None
        self.scroll_progress = 0

    def hit_check(self, hit):
        if hit:
            if not self.last_hit_time:
                self.last_hit_time = time.perf_counter()
        else:
            hit = False
            self.last_hit_time = None

        self.hit = hit


class clickless_mouse:
    def __init__(self):
        self.button_positions = []
        self.screen = None
        self.mcanvas = None
        self.x, self.y = ctrl.mouse_pos()
        self._dwell_x, self._dwell_y = ctrl.mouse_pos()
        self.state = STATE_MOUSE_IDLE
        self.last_time = 0
        self.enabled = False
        self.update_cron = None
        self.draw_registered = False

        # the bounds around the displayed options. if you go outside, options
        # are hidden
        self.y_min = self.y_max = self.x_min = self.x_max = 0

    def is_left_down(self):
        return left_mouse_button_index in ctrl.mouse_buttons_down()

    def enable(self, enable):
        self.enabled = enable
        if enable == self.enable:
            return

        self.enabled = enable
        if enable:
            actions.mode.enable("user.clickless_mouse_enabled")
        else:
            actions.mode.disable("user.clickless_mouse_enabled")

        if self.enabled:
            self.update_cron = cron.interval("16ms", self.update)
        elif self.update_cron:
            cron.cancel(self.update_cron)
            self.update_cron = None
            if self.draw_registered:
                self.mcanvas.unregister("draw", self.draw)
                self.mcanvas.close()
                self.mcanvas = None

    def toggle(self):
        self.enable(not self.enabled)

    def set_button_positions(self):
        self.button_positions = []
        self.scroll_progress = 0
        self.x, self.y = ctrl.mouse_pos()

        self._dwell_x, self._dwell_y = self.x, self.y

        # alias the cursor position for convenience
        x = self.x
        y = self.y

        # calculate the screen coordinates
        x_screen = self.x - self.screen.x
        y_screen = self.y - self.screen.y

        # upper left corner
        if x_screen <= radius.get() * 3.5 and y_screen <= radius.get() * 3.25:
            # print("case 1")

            y_pos = y + math.ceil(radius.get() * 3)
            x_pos = None
            for index, button_label in enumerate(horizontal_button_order):
                x_pos = x + math.ceil(radius.get() * (2.5 + 2.25 * (index - 1)))
                self.button_positions.append(
                    dwell_button(
                        x_pos,
                        y_pos,
                        button_label if not self.is_left_down() else "lr",
                    )
                )
                # print("{},{}".format(x_pos, y_pos))

            self.y_min = self.screen.y - 2 * radius.get()
            self.y_max = y + math.ceil(radius.get() * 5)
            self.x_min = self.screen.x - 2 * radius.get()
            self.x_max = x + radius.get() * (len(horizontal_button_order) + 1) * 2

        # upper right corner
        elif (
            x_screen + radius.get() * 3.5 >= self.screen.width
            and y_screen <= radius.get() * 3.25
        ):
            # print("case 2")
            y_pos = y + math.ceil(radius.get() * 3)
            x_pos = None
            for index, button_label in enumerate(horizontal_button_order):
                x_pos = x - math.ceil(radius.get() * (2.5 + 2.25 * (index - 1)))
                self.button_positions.append(
                    dwell_button(
                        x_pos,
                        y_pos,
                        button_label if not self.is_left_down() else "lr",
                    )
                )

            self.y_min = self.screen.y - 2 * radius.get()
            self.y_max = y + math.ceil(radius.get() * 5)
            self.x_min = x - math.ceil(
                radius.get() * (len(horizontal_button_order) + 1) * 2
            )
            self.x_max = x + math.ceil(radius.get() * 2)

        # lower left corner
        elif (
            x_screen <= radius.get() * 3.5
            and y_screen + radius.get() * 3.25 >= self.screen.height
        ):
            # print("case 3")
            y_pos = y - math.ceil(radius.get() * 3)
            x_pos = None
            for index, button_label in enumerate(horizontal_button_order):
                x_pos = x + math.ceil(radius.get() * (2.5 + 2.25 * (index - 1)))
                self.button_positions.append(
                    dwell_button(
                        x_pos,
                        y_pos,
                        button_label if not self.is_left_down() else "lr",
                    )
                )

            # todo: something better for the bounds
            self.y_min = y - math.ceil(radius.get() * 5)
            self.y_max = y + math.ceil(radius.get() * 4)
            self.x_min = x - math.ceil(radius.get() * 4)
            self.x_max = x + math.ceil(
                radius.get() * (len(horizontal_button_order) + 1) * 2
            )

        # lower right corner
        elif (
            x_screen + radius.get() * 3.5 >= self.screen.width
            and y_screen + math.ceil(radius.get() * 3.25) >= self.screen.height
        ):
            # print("case 4")
            x_pos = None
            y_pos = y - math.ceil(radius.get() * 3)
            for index, button_label in enumerate(horizontal_button_order):
                x_pos = x - math.ceil(radius.get() * (2.5 + 2.25 * (index - 1)))
                self.button_positions.append(
                    dwell_button(
                        x_pos,
                        y_pos,
                        button_label if not self.is_left_down() else "lr",
                    )
                )

            self.y_min = y - math.ceil(radius.get() * 5)
            self.y_max = (
                self.screen.y + self.screen.height + math.ceil(radius.get() * 4)
            )
            self.x_min = x - math.ceil(
                radius.get() * (len(horizontal_button_order) + 1) * 2
            )
            self.x_max = x + math.ceil(radius.get() * 4)

        # bottom edge, sufficient space to draw to the right
        elif (
            y_screen + math.ceil(radius.get() * 3.25) >= self.screen.height
            and x_screen + math.ceil(radius.get() * len(horizontal_button_order) * 2)
            <= self.screen.width
        ):
            # print("case 5")
            x_pos = None
            y_pos = y - math.ceil(radius.get() * 3)
            for index, button_label in enumerate(horizontal_button_order):
                x_pos = x + math.ceil(radius.get() * (2.5 + 2.25 * (index - 1)))
                self.button_positions.append(
                    dwell_button(
                        x_pos,
                        y_pos,
                        button_label if not self.is_left_down() else "lr",
                    )
                )

            self.y_min = y - math.ceil(radius.get() * 5)
            self.y_max = (
                self.screen.y + self.screen.height + math.ceil(radius.get() * 4)
            )
            self.x_min = x - math.ceil(radius.get() * 4)
            self.x_max = x + math.ceil(
                radius.get() * (len(horizontal_button_order) + 1) * 2
            )

        # bottom edge, insufficient space to draw to the right
        elif (
            y_screen + math.ceil(radius.get() * 3.25) >= self.screen.height
            and x_screen + math.ceil(radius.get() * len(horizontal_button_order) * 2)
            >= self.screen.width
        ):
            # print("case 6")
            x_pos = None
            y_pos = y - self.screen.y - math.ceil(radius.get() * 4)
            for index, button_label in enumerate(horizontal_button_order):
                x_pos = (
                    x
                    - self.screen.x
                    - math.ceil(radius.get() * (2.5 + 2.25 * (index - 1)))
                )
                self.button_positions.append(
                    dwell_button(
                        x_pos,
                        y_pos,
                        button_label if not self.is_left_down() else "lr",
                    )
                )

            self.y_min = y - math.ceil(radius.get() * 5)
            self.y_max = self.screen.height + math.ceil(radius.get() * 4)
            self.x_min = x - math.ceil(
                radius.get() * (len(horizontal_button_order) + 1) * 2
            )
            self.x_max = x + math.ceil(radius.get() * 2)

        # left edge, not in corner
        elif x_screen <= radius.get() * 3.5:
            # print("case 7")

            x_pos = None
            y_pos = y + math.ceil(radius.get() * 3)
            for index, button_label in enumerate(horizontal_button_order):
                x_pos = x + math.ceil(radius.get() * (2.5 + 2.25 * (index - 1)))
                self.button_positions.append(
                    dwell_button(
                        x_pos,
                        y_pos,
                        button_label if not self.is_left_down() else "lr",
                    )
                )

            self.y_min = y - math.ceil(radius.get() * 4)
            self.y_max = y + math.ceil(radius.get() * 5)
            self.x_min = x - math.ceil(radius.get() * 2)
            self.x_max = x + math.ceil(
                radius.get() * (len(horizontal_button_order) + 1) * 2
            )

        # right edge, not in corner
        elif x_screen + radius.get() * 3.5 >= self.screen.width:
            # print("case 8")
            x_pos = None
            y_pos = y + math.ceil(radius.get() * 3)
            for index, button_label in enumerate(horizontal_button_order):
                x_pos = x - math.ceil(radius.get() * (2.5 + 2.25 * (index - 1)))
                self.button_positions.append(
                    dwell_button(
                        x_pos,
                        y_pos,
                        button_label if not self.is_left_down() else "lr",
                    )
                )

            self.y_min = y - math.ceil(radius.get() * 4)
            self.y_max = y + math.ceil(radius.get() * 5)
            self.x_min = x - math.ceil(
                radius.get() * (len(horizontal_button_order) + 1) * 2
            )
            self.x_max = x + math.ceil(radius.get() * 2)

        # not along edges and not in corner
        # draw all around cursor
        elif (
            not y_screen <= radius.get() * 3.25
            and x_screen + radius.get() * 3.5 <= self.screen.width
        ):
            # print("case 9")
            self.button_positions.append(
                dwell_button(
                    x - math.ceil(radius.get() * 2.25),
                    y - math.ceil(radius.get() * 2),
                    "su" if not self.is_left_down() else "lr",
                )
            )
            self.button_positions.append(
                dwell_button(
                    x + math.ceil(radius.get() * 2.25),
                    y - math.ceil(radius.get() * 2),
                    "sd" if not self.is_left_down() else "lr",
                )
            )
            self.button_positions.append(
                dwell_button(
                    x,
                    y - math.ceil(radius.get() * 3.25),
                    "lt" if not self.is_left_down() else "lr",
                )
            )

            self.button_positions.append(
                dwell_button(
                    x - math.ceil(radius.get() * 3.5),
                    y,
                    "lh" if not self.is_left_down() else "lr",
                )
            )
            self.button_positions.append(
                dwell_button(
                    x - math.ceil(radius.get() * 2.25),
                    y + math.ceil(radius.get() * 2),
                    "ld" if not self.is_left_down() else "lr",
                )
            )

            self.button_positions.append(
                dwell_button(
                    x,
                    y + math.ceil(radius.get() * 3.25),
                    "l" if not self.is_left_down() else "lr",
                )
            )

            self.button_positions.append(
                dwell_button(
                    x + math.ceil(radius.get() * 2.25),
                    y + math.ceil(radius.get() * 2),
                    "r" if not self.is_left_down() else "lr",
                )
            )
            self.button_positions.append(
                dwell_button(
                    x + math.ceil(radius.get() * 3.5),
                    y,
                    "ka" if not self.is_left_down() else "lr",
                )
            )

            self.y_min = y - math.ceil(radius.get() * 7)
            self.y_max = y + math.ceil(radius.get() * 7)
            self.x_min = x - math.ceil(radius.get() * 7)
            self.x_max = x + math.ceil(radius.get() * 7)

        # top edge, sufficient space to the right
        elif (
            y_screen <= radius.get() * 3.25
            and x_screen + radius.get() * 3.5 <= self.screen.width
            and x_screen + math.ceil(radius.get() * len(horizontal_button_order) * 2)
            <= self.screen.width
        ):
            # print("case 10")
            x_pos = None
            y_pos = y + math.ceil(radius.get() * 3)
            for index, button_label in enumerate(horizontal_button_order):
                x_pos = x + math.ceil(radius.get() * (2.5 + 2.25 * (index - 1)))
                self.button_positions.append(
                    dwell_button(
                        x_pos,
                        y_pos,
                        button_label if not self.is_left_down() else "lr",
                    )
                )

            self.y_min = y - math.ceil(radius.get() * 4)
            self.y_max = y + math.ceil(radius.get() * 5)
            self.x_min = x - math.ceil(radius.get() * 2)
            self.x_max = x + math.ceil(
                radius.get() * (len(horizontal_button_order) + 1) * 2
            )

        # top edge, insufficient space to the right
        elif (
            x_screen + radius.get() * 3.5 <= self.screen.width
            and (
                x_screen + math.ceil(radius.get() * len(horizontal_button_order) * 2)
                >= self.screen.width
            )
            and y_screen <= radius.get() * 3.25
        ):
            # print("case 11")
            x_pos = None
            y_pos = y + math.ceil(radius.get() * 3)
            for index, button_label in enumerate(horizontal_button_order):
                x_pos = x - math.ceil(radius.get() * (2.5 + 2.25 * (index - 1)))
                self.button_positions.append(
                    dwell_button(
                        x_pos,
                        y_pos,
                        button_label,
                    )
                )

            self.y_min = y - math.ceil(radius.get() * 4)
            self.y_max = y + math.ceil(radius.get() * 5)
            self.x_min = x - math.ceil(
                radius.get() * (len(horizontal_button_order) + 1) * 2
            )
            self.x_max = x + math.ceil(radius.get() * 2)
        # top edge, insufficient space to the right
        elif (
            x_screen + radius.get() * 3.5 >= self.screen.width
            and y_screen <= radius.get() * 3.25
        ):
            # print("case 12")
            x_pos = None
            y_pos = y + math.ceil(radius.get() * 3)
            for index, button_label in enumerate(horizontal_button_order):
                x_pos = x - math.ceil(radius.get() * (2.5 + 2.25 * (index - 1)))
                self.button_positions.append(
                    dwell_button(
                        x_pos,
                        y_pos,
                        button_label,
                    )
                )

            self.y_min = y - math.ceil(radius.get() * 5)
            self.y_max = y + math.ceil(radius.get() * 5)
            self.x_min = x - math.ceil(
                radius.get() * (len(horizontal_button_order) + 1) * 2
            )
            self.x_max = x + math.ceil(radius.get() * 2)
        else:
            print("not handled: {},{}".format(x, y))

        # print(self.button_positions)

    def update(self):
        # print("update")
        x, y = ctrl.mouse_pos()
        now = time.perf_counter()
        # print("({},{})".format(x,y))
        if self.state == STATE_MOUSE_IDLE:
            # print("idle")

            if x != self.x and y != self.y:
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
                if now - self.last_time >= mouse_idle.get():
                    self.last_time = now
                    self._dwell_x, self._dwell_y = ctrl.mouse_pos()
                    screen = ui.screen_containing(self.x, self.y)

                    # if the screen is cached, it won't always appear over
                    # certain windows
                    if True:  # screen != self.screen:
                        self.screen = screen
                        if self.mcanvas:
                            self.mcanvas.close()
                            self.mcanvas = None
                        self.mcanvas = canvas.Canvas.from_screen(self.screen)
                        # print(self.mcanvas.rect)
                        # print(ctrl.mouse_pos())

                    # print(str(screen))
                    # print(str(ctrl.mouse_pos()))
                    self.set_button_positions()
                    self.state = STATE_DISPLAYING_OPTIONS
            else:
                self.x, self.y = ctrl.mouse_pos()
                self.state = STATE_MOUSE_MOVING
                self.button_positions = []
        elif self.state == STATE_DISPLAYING_OPTIONS:
            # print("display")
            item_hit = None
            draw_options = True
            for b in self.button_positions:
                if (x <= b.x + radius.get() and b.x - radius.get() <= x) and (
                    y <= b.y + radius.get() and b.y - radius.get() <= y
                ):
                    b.hit_check(True)
                    self.last_time = now
                    item_hit = b
                else:
                    b.hit_check(False)

            if (
                not item_hit
                and now - self.last_time >= auto_hide.get()
                and (self._dwell_x == x or self._dwell_y == y)
            ):
                # update the position to prevent re-display for minor moves
                # this may not be preferred.
                if prevent_redisplay_for_minor_motions.get() >= 1:
                    self.x = self._dwell_x
                    self.y = self._dwell_y

                self.state = STATE_MOUSE_IDLE
                draw_options = False

            elif item_hit and now - item_hit.last_hit_time >= dwell_time.get():
                draw_options = False

                # print("performing action...")
                action = item_hit.action
                if action != "su" and action != "sd" and action != "ka":
                    ctrl.mouse_move(self.x, self.y)

                if item_hit.action == "lh":
                    # print("left hold")
                    if not self.is_left_down():
                        # print("pressing button 0 down")
                        ctrl.mouse_click(button=left_mouse_button_index, down=True)
                    else:
                        # print("pressing button 0 up")
                        actions.sleep("{}ms".format(release_button_delay.get()))
                        ctrl.mouse_click()
                        ctrl.mouse_click(button=left_mouse_button_index, up=True)

                    # print(str(ctrl.mouse_buttons_down()))
                elif item_hit.action == "lr":
                    if self.is_left_down():
                        actions.sleep("{}ms".format(release_button_delay.get()))
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
                    ctrl.mouse_click(button=1)

                elif item_hit.action == "rh":
                    if right_mouse_button_index not in ctrl.mouse_buttons_down():
                        ctrl.mouse_click(button=right_mouse_button_index, down=True)
                    else:
                        actions.sleep("{}ms".format(release_button_delay.get()))
                        ctrl.mouse_click(button=right_mouse_button_index, up=True)
                elif item_hit.action == "su":
                    actions.mouse_scroll(y=-10)
                    draw_options = True

                elif item_hit.action == "sd":
                    actions.mouse_scroll(y=10)
                    draw_options = True
                elif item_hit.action == "ka":
                    draw_options = True

                if action != "su" and action != "sd" and action != "ka":
                    self.x, self.y = ctrl.mouse_pos()
                    self.state = STATE_MOUSE_IDLE
                    self.scroll_progress = 0

            elif x > self.x_max or x < self.x_min or y > self.y_max or y < self.y_min:
                draw_options = False
                self.state = STATE_MOUSE_IDLE

            if draw_options:
                if self._dwell_x != x or self._dwell_y != y:
                    self.last_time = now
                    self._dwell_x, self._dwell_y = ctrl.mouse_pos()

                if not self.draw_registered:
                    self.mcanvas.register("draw", self.draw)
                    self.draw_registered = True
            elif self.draw_registered:
                self.mcanvas.unregister("draw", self.draw)
                self.draw_registered = False

    def draw(self, canvas):
        self.draw_options(canvas)

    def draw_options(self, canvas):
        x = self.x
        y = self.y
        paint = canvas.paint
        paint.color = "ff0000"
        paint.style = paint.Style.FILL
        # print("{},{}".format(self.x, self.y))
        # print(canvas.rect)
        canvas.draw_line(x - radius.get(), y, x + radius.get(), y)
        canvas.draw_line(x, y - radius.get(), x, y + radius.get())

        for b in self.button_positions:
            # draw outer circle
            paint.color = "ffffffaa"
            paint.style = paint.Style.STROKE
            canvas.draw_circle(b.x, b.y, radius.get() + 1)

            # draw inner circle
            paint.color = "000000AA"
            paint.style = paint.Style.STROKE
            paint.style = paint.Style.FILL
            canvas.draw_circle(b.x, b.y, radius.get())

            # draw hit circle
            if b.last_hit_time:
                paint.color = "00FF00"
                paint.style = paint.Style.FILL

                _radius = min(
                    math.ceil(
                        radius.get()
                        * (time.perf_counter() - b.last_hit_time)
                        / dwell_time.get()
                    ),
                    radius.get(),
                )
                canvas.draw_circle(b.x, b.y, _radius)

            canvas.paint.text_align = canvas.paint.TextAlign.CENTER
            text_string = b.action
            paint.textsize = radius.get()
            paint.color = "ffffffff"

            canvas.draw_text(text_string, b.x, b.y)


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


# uncomment the following for quick testing
# def on_ready():
#     cm.enable(True)


# app.register("ready", on_ready)
