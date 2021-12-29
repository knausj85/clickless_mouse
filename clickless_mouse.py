# prototype of a clickless mouse mode using Talon. This does not coexist with the zoom, control mouse or mouse grid
# todo:
#  (1) multi-monitor support
#  (2) smoother, accelerated scrolling
#  (3) horizontal scrolling

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

mod = Module()
ctx = Context()
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
        self.offset_x = None
        self.offset_y = None
        self.width = None
        self.height = None
        self.mcanvas = None
        self.x, self.y = ctrl.mouse_pos()
        self._dwell_x, self._dwell_y = ctrl.mouse_pos()
        self.state = STATE_MOUSE_IDLE
        self.last_time = 0
        self.enabled = False
        self.update_cron = None
        self.draw_registered = False
        self.y_min = self.y_max = self.x_min = self.x_max = 0

    def __del__(self):
        self.mcanvas = None

    def is_left_down(self):
        left_index = 0

        return left_index in ctrl.mouse_buttons_down()

    def enable(self, enable):
        self.enabled = enable

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
        x = self.x
        y = self.y

        # upper left corner
        if x <= radius.get() * 3.5 and y <= radius.get() * 3.25:
            # print("case 1")
            # print("x <= 70 and y <= 65")

            y_pos = y + math.ceil(radius.get() * 2)
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

            self.y_min = -2 * radius.get()
            self.y_max = y + math.ceil(radius.get() * 4)
            self.x_min = -2 * radius.get()
            self.x_max = x + radius.get() * (len(horizontal_button_order) + 1) * 2

        # upper right corner
        elif x + radius.get() * 3.5 >= self.width and y <= radius.get() * 3.25:
            # print("case 2")
            y_pos = y + math.ceil(radius.get() * 2)
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

            self.y_min = -2 * radius.get()
            self.y_max = y + math.ceil(radius.get() * 4)
            self.x_min = x - math.ceil(
                radius.get() * (len(horizontal_button_order) + 1) * 2
            )
            self.x_max = x + math.ceil(radius.get() * 2)

        # lower left corner
        elif x <= radius.get() * 3.5 and y + radius.get() * 3.25 >= self.height:
            # print("x <= 70 and y + 65 >= self.height")
            # print("case 3")
            y_pos = y - math.ceil(radius.get() * 2)
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

            self.y_min = y - math.ceil(radius.get() * 4)
            self.y_max = y + math.ceil(radius.get() * 4)
            self.x_min = x - math.ceil(radius.get() * 4)
            self.x_max = x + math.ceil(
                radius.get() * (len(horizontal_button_order) + 1) * 2
            )

        # lower right corner
        elif (
            x + radius.get() * 3.5 >= self.width
            and y + math.ceil(radius.get() * 3.25) >= self.height
        ):
            x_pos = None
            y_pos = y - math.ceil(radius.get() * 2)
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
            self.y_max = self.height + math.ceil(radius.get() * 4)
            self.x_min = x - math.ceil(
                radius.get() * (len(horizontal_button_order) + 1) * 2
            )
            self.x_max = x + math.ceil(radius.get() * 4)

        # bottom edge, sufficient space to draw to the right
        elif (
            y + math.ceil(radius.get() * 3.25) >= self.height
            and x + math.ceil(radius.get() * 16) <= self.width
        ):
            # print("case 5")
            x_pos = None
            y_pos = y - math.ceil(radius.get() * 2)
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
            self.y_max = self.height + math.ceil(radius.get() * 4)
            self.x_min = x - math.ceil(radius.get() * 4)
            self.x_max = x + math.ceil(
                radius.get() * (len(horizontal_button_order) + 1) * 2
            )

        # bottom edge, insufficient space to draw to the right
        elif (
            y + math.ceil(radius.get() * 3.25) >= self.height
            and x + math.ceil(radius.get() * 16) >= self.width
        ):
            # print("case 5")
            x_pos = None
            y_pos = y - math.ceil(radius.get() * 2)
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
            self.y_max = self.height + math.ceil(radius.get() * 4)
            self.x_min = x - math.ceil(
                radius.get() * (len(horizontal_button_order) + 1) * 2
            )
            self.x_max = x + math.ceil(radius.get() * 2)

        elif x <= radius.get() * 3.5:
            # print("case 6")

            x_pos = None
            y_pos = y + math.ceil(radius.get() * 2)
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
            self.y_max = y + math.ceil(radius.get() * 4)
            self.x_min = x - math.ceil(radius.get() * 2)
            self.x_max = x + math.ceil(
                radius.get() * (len(horizontal_button_order) + 1) * 2
            )

        elif x + radius.get() * 3.5 >= self.width:
            # print("case 7")
            x_pos = None
            y_pos = y + math.ceil(radius.get() * 2)
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
            self.y_max = y + math.ceil(radius.get() * 4)
            self.x_min = x - math.ceil(
                radius.get() * (len(horizontal_button_order) + 1) * 2
            )
            self.x_max = x + math.ceil(radius.get() * 2)

        elif not y <= radius.get() * 3.25 and x + radius.get() * 3.5 <= self.width:
            # print("case 8")
            # print("y + 65 < self.height and x + 70 < self.width")
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

        elif (
            x + radius.get() * 3.5 <= self.width
            and y <= radius.get() * 3.25
            and x + math.ceil(radius.get() * 13.75)
        ) <= self.width:
            # print("case 9")
            x_pos = None
            y_pos = y + math.ceil(radius.get() * 2)
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
            self.y_max = y + math.ceil(radius.get() * 4)
            self.x_min = x - math.ceil(radius.get() * 2)
            self.x_max = x + math.ceil(
                radius.get() * (len(horizontal_button_order) + 1) * 2
            )

        elif (
            x - self.offset_x + radius.get() * 3.5 <= self.width
            and y - self.offset_y <= radius.get() * 3.25
            and x - self.offset_x + math.ceil(radius.get() * 13.75)
        ) >= self.width:
            # print("case 10")
            x_pos = None
            y_pos = y + math.ceil(radius.get() * 2)
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
            self.y_max = y + math.ceil(radius.get() * 4)
            self.x_min = x - math.ceil(
                radius.get() * (len(horizontal_button_order) + 1) * 2
            )
            self.x_max = x + math.ceil(radius.get() * 2)

        elif (
            x - self.offset_x + radius.get() * 3.5 >= self.width
            and y - self.offset_y <= radius.get() * 3.25
        ):
            # print("case 11")
            x_pos = None
            y_pos = y + math.ceil(radius.get() * 2)
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
            self.y_max = y + math.ceil(radius.get() * 4)
            self.x_min = x - math.ceil(
                radius.get() * (len(horizontal_button_order) + 1) * 2
            )
            self.x_max = x + math.ceil(radius.get() * 2)
        else:
            print("not handled: {},{}".format(x, y))

    def update(self):
        # print("update")
        x, y = ctrl.mouse_pos()
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
                self.last_time = time.perf_counter()
                self.state = STATE_MOUSE_STOPPED
            else:
                self.x, self.y = ctrl.mouse_pos()

        elif self.state == STATE_MOUSE_STOPPED:
            # print("stopped")

            if x == self.x and y == self.y:
                if time.perf_counter() - self.last_time >= mouse_idle.get():
                    self.last_time = time.perf_counter()
                    self._dwell_x, self._dwell_y = ctrl.mouse_pos()
                    screen = ui.screen_containing(self.x, self.y)

                    # if screen != self.screen:
                    self.screen = screen
                    self.offset_x = self.screen.x
                    self.offset_y = self.screen.y
                    self.width = self.screen.width
                    self.height = self.screen.height
                    self.mcanvas = None
                    self.mcanvas = canvas.Canvas.from_screen(self.screen)

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
                    self.last_time = time.perf_counter()
                    item_hit = b
                else:
                    b.hit_check(False)

            if (
                not item_hit
                and time.perf_counter() - self.last_time >= auto_hide.get()
                and (self._dwell_x == x or self._dwell_y == y)
            ):
                # update the position to prevent re-display for minor moves
                # this may not be preferred.
                # self.x = self._dwell_x
                # self.y = self._dwell_y

                self.state = STATE_MOUSE_IDLE
                draw_options = False

            elif (
                item_hit
                and time.perf_counter() - item_hit.last_hit_time >= dwell_time.get()
            ):
                draw_options = False

                # print("performing action...")
                action = item_hit.action
                if action != "su" and action != "sd" and action != "ka":
                    ctrl.mouse_move(self.x, self.y)

                if item_hit.action == "lh":
                    # print("left hold")
                    if not self.is_left_down():
                        # print("pressing button 0 down")
                        ctrl.mouse_click(button=0, down=True)
                    else:
                        # print("pressing button 0 up")
                        actions.sleep("{}ms".format(release_button_delay.get()))
                        ctrl.mouse_click()
                        ctrl.mouse_click(button=0, up=True)

                    # print(str(ctrl.mouse_buttons_down()))
                elif item_hit.action == "lr":
                    if self.is_left_down():
                        actions.sleep("{}ms".format(release_button_delay.get()))
                        ctrl.mouse_click(button=0, up=True)

                elif item_hit.action == "l":
                    ctrl.mouse_click(button=0, hold=16000)

                elif item_hit.action == "ld":
                    ctrl.mouse_click(button=0, hold=16000)
                    ctrl.mouse_click(button=0, hold=16000)

                elif item_hit.action == "lt":
                    ctrl.mouse_click(button=0, hold=16000)
                    ctrl.mouse_click(button=0, hold=16000)
                    ctrl.mouse_click(button=0, hold=16000)

                elif item_hit.action == "r":
                    ctrl.mouse_click(button=1, hold=16000)

                elif item_hit.action == "rh":
                    index = 1
                    if index not in ctrl.mouse_buttons_down():
                        ctrl.mouse_click(button=1, down=True)
                    else:
                        actions.sleep("50ms")
                        ctrl.mouse_click(button=1, up=True)
                        # print(str(ctrl.mouse_buttons_down()))
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
                    self.last_time = time.perf_counter()
                    self._dwell_x, self._dwell_y = ctrl.mouse_pos()

                # print("draw options...")
                if not self.draw_registered:
                    self.mcanvas.register("draw", self.draw)
                    self.draw_registered = True
            elif self.draw_registered:
                self.mcanvas.unregister("draw", self.draw)
                self.draw_registered = False

    def draw(self, canvas):
        self.draw_options(canvas)

    def draw_options(self, canvas):
        paint = canvas.paint
        paint.color = "ff0000"
        paint.style = paint.Style.FILL
        canvas.draw_circle(self.x, self.y, 3.5)

        for b in self.button_positions:
            # draw outer circle
            paint.color = "ffffffAA"
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

            # text_rect = canvas.paint.measure_text(text_string)[1]
            canvas.draw_text(text_string, b.x, b.y)


cm = clickless_mouse()


@mod.action_class
class Actions:
    def clickless_mouse_toggle():
        """Toggles the click less mouse"""
        cm.toggle()


# uncomment for quick testing
cm.enable(True)
