import time
from talon import canvas, screen, ui, ctrl, settings
from .dwell_button import dwell_button
import math

# l = left click
# lh = left hold
# lr = left release. when left is down, all options become lr
# ld = left double click
# su = scroll up
# sd = scroll down
# r = right click
# rh = right click old, DISABLED, doesn't work yet.
# ka = keep alive for e.g. leaving the thing up for easy scroll down/up on webpages. no action
# x = force an exit when auto hide is disabled
horizontal_button_order_auto_hide_enabled = [
    "l",
    "ld",
    "lt",
    "lh",
    "r",
    "su",
    "sd",
    "ka",
]
horizontal_button_order_auto_hide_disabled = [
    "l",
    "ld",
    "lt",
    "lh",
    "r",
    "su",
    "sd",
    "x",
]

left_mouse_button_index = 0
right_mouse_button_index = 1

class dwell_panel:
    def __init__(self):
        self.button_positions = []
        self.x, self.y = ctrl.mouse_pos()
        self._dwell_x, self._dwell_y = self.x, self.y
        self.screen = None
        self.mcanvas = None
        self.draw_registered = False
        self.panel_x, self.panel_y = None, None


        # the bounds around the displayed options. if you go outside, options
        # are hidden
        self.y_min = self.y_max = self.x_min = self.x_max = 0

    def unregister_and_close_canvas(self):
        if self.draw_registered:
            self.mcanvas.unregister("draw", self.draw)
            self.mcanvas.close()
            self.mcanvas = None
            self.draw_registered = False

    def register_canvas(self):
        if not self.draw_registered:
            self.mcanvas.register("draw", self.draw)
            self.draw_registered = True

    def unregister_canvas(self):
        if self.draw_registered:
            self.mcanvas.unregister("draw", self.draw)
            self.draw_registered = False

    def get_max_horizontal_distance(self):
        return 2 * settings.get("user.clickless_mouse_radius") * (len(self.get_horizontal_button_order()) + 1.5)

    def get_horizontal_button_order(self):
        if settings.get("user.clickless_mouse_auto_hide") >= 1:
            return horizontal_button_order_auto_hide_enabled
        else:
            return horizontal_button_order_auto_hide_disabled

    def set_button_positions(self, x, y, is_left_down):
        self.button_positions = []
        self.x, self.y = x, y

        self._dwell_x, self._dwell_y = self.x, self.y

        # alias the cursor position for convenience
        x = self.x
        y = self.y

        # calculate the screen coordinates
        x_screen = self.x - self.screen.x
        y_screen = self.y - self.screen.y

        # top left corner
        if x_screen <= settings.get("user.clickless_mouse_radius") * 3.5 and y_screen <= settings.get("user.clickless_mouse_radius") * 3.25:
            # print("case 1")
            self.set_horizontal_button_positions_and_bounds(x, y, True, False, is_left_down)

        # top right corner
        elif (
            x_screen + settings.get("user.clickless_mouse_radius") * 3.5 >= self.screen.width
            and y_screen <= settings.get("user.clickless_mouse_radius") * 3.25
        ):
            # print("case 2")
            self.set_horizontal_button_positions_and_bounds(x, y, False, False, is_left_down)

        # bottom left corner
        elif (
            x_screen <= settings.get("user.clickless_mouse_radius") * 3.5
            and y_screen + settings.get("user.clickless_mouse_radius") * 3.25 >= self.screen.height
        ):
            # print("case 3")
            self.set_horizontal_button_positions_and_bounds(x, y, True, True, is_left_down)

        # bottom right corner
        elif (
            x_screen + settings.get("user.clickless_mouse_radius") * 3.5 >= self.screen.width
            and y_screen + math.ceil(settings.get("user.clickless_mouse_radius") * 3.25) >= self.screen.height
        ):
            # print("case 4")
            self.set_horizontal_button_positions_and_bounds(x, y, False, True, is_left_down)

        # bottom edge, sufficient space to draw to the right
        elif (
            y_screen + math.ceil(settings.get("user.clickless_mouse_radius") * 3.25) >= self.screen.height
            and x_screen
            + math.ceil(settings.get("user.clickless_mouse_radius") * len(self.get_horizontal_button_order()) * 2)
            <= self.screen.width
        ):
            # print("case 5")
            self.set_horizontal_button_positions_and_bounds(x, y, True, True, is_left_down)

        # bottom edge, insufficient space to draw to the right
        elif (
            y_screen + math.ceil(settings.get("user.clickless_mouse_radius") * 3.25) >= self.screen.height
            and x_screen
            + math.ceil(settings.get("user.clickless_mouse_radius") * len(self.get_horizontal_button_order()) * 2)
            >= self.screen.width
        ):
            # print("case 6")
            self.set_horizontal_button_positions_and_bounds(x, y, False, True, is_left_down)

        # left edge, not in corner
        elif x_screen <= settings.get("user.clickless_mouse_radius") * 3.5:
            # print("case 7")
            self.set_horizontal_button_positions_and_bounds(x, y, True, False, is_left_down)

        # right edge, not in corner
        elif x_screen + settings.get("user.clickless_mouse_radius") * 3.5 >= self.screen.width:
            # print("case 8")
            self.set_horizontal_button_positions_and_bounds(x, y, False, False, is_left_down)

        # not along edges and not in corner
        # draw all around cursor
        elif (
            not y_screen <= settings.get("user.clickless_mouse_radius") * 3.25
            and x_screen + settings.get("user.clickless_mouse_radius") * 3.5 <= self.screen.width
        ):
            # print("case 9")
            self.button_positions.append(
                dwell_button(
                    x - math.ceil(settings.get("user.clickless_mouse_radius") * 2.25),
                    y - math.ceil(settings.get("user.clickless_mouse_radius") * 2.25),
                    "su" if not is_left_down else "lr",
                )
            )
            self.button_positions.append(
                dwell_button(
                    x + math.ceil(settings.get("user.clickless_mouse_radius") * 2.25),
                    y - math.ceil(settings.get("user.clickless_mouse_radius") * 2.25),
                    "sd" if not is_left_down else "lr",
                )
            )
            self.button_positions.append(
                dwell_button(
                    x,
                    y - math.ceil(settings.get("user.clickless_mouse_radius") * 2.25),
                    "lt" if not is_left_down else "lr",
                )
            )

            self.button_positions.append(
                dwell_button(
                    x - math.ceil(settings.get("user.clickless_mouse_radius") * 3.5),
                    y,
                    "lh" if not is_left_down else "lr",
                )
            )
            self.button_positions.append(
                dwell_button(
                    x - math.ceil(settings.get("user.clickless_mouse_radius") * 2.25),
                    y + math.ceil(settings.get("user.clickless_mouse_radius") * 2.25),
                    "ld" if not is_left_down else "lr",
                )
            )

            self.button_positions.append(
                dwell_button(
                    x,
                    y + math.ceil(settings.get("user.clickless_mouse_radius") * 2.25),
                    "l" if not is_left_down else "lr",
                )
            )

            self.button_positions.append(
                dwell_button(
                    x + math.ceil(settings.get("user.clickless_mouse_radius") * 2.25),
                    y + math.ceil(settings.get("user.clickless_mouse_radius") * 2.25),
                    "r" if not is_left_down else "lr",
                )
            )

            action = "ka" if settings.get("user.clickless_mouse_auto_hide") >= 1 else "x"
            self.button_positions.append(
                dwell_button(x + math.ceil(settings.get("user.clickless_mouse_radius") * 3.5), y, action)
            )

            self.y_min = y - math.ceil(settings.get("user.clickless_mouse_radius") * 5)
            self.y_max = y + math.ceil(settings.get("user.clickless_mouse_radius") * 5)
            self.x_min = x - math.ceil(settings.get("user.clickless_mouse_radius") * 5)
            self.x_max = x + math.ceil(settings.get("user.clickless_mouse_radius") * 5)

        # top edge, sufficient space to the right
        elif (
            y_screen <= settings.get("user.clickless_mouse_radius") * 3.25
            and x_screen + settings.get("user.clickless_mouse_radius") * 3.5 <= self.screen.width
            and x_screen
            + math.ceil(settings.get("user.clickless_mouse_radius") * len(self.get_horizontal_button_order()) * 2)
            <= self.screen.width
        ):
            # print("case 10")
            self.set_horizontal_button_positions_and_bounds(x, y, True, False, is_left_down)

        # top edge, insufficient space to the right
        elif (
            x_screen + settings.get("user.clickless_mouse_radius") * 3.5 <= self.screen.width
            and (
                x_screen
                + math.ceil(
                    settings.get("user.clickless_mouse_radius") * len(self.get_horizontal_button_order()) * 2
                )
                >= self.screen.width
            )
            and y_screen <= settings.get("user.clickless_mouse_radius") * 3.25
        ):
            # print("case 11")
            self.set_horizontal_button_positions_and_bounds(x, y, False, False, is_left_down)

        else:
            print("not handled: {},{}".format(x, y))

        # print(self.button_positions)

    def set_horizontal_button_positions_and_bounds(self, x, y, draw_right, draw_above, is_left_down):
        x_pos = None

        if draw_above:
            y_pos = y - math.ceil(settings.get("user.clickless_mouse_radius") * settings.get("user.clickless_mouse_vertical_offset"))  
            self.y_min = y - math.ceil(settings.get("user.clickless_mouse_radius") * 5)
            self.y_max = y + math.ceil(settings.get("user.clickless_mouse_radius") * 2)      
        else:
            y_pos = y + math.ceil(settings.get("user.clickless_mouse_radius") * settings.get("user.clickless_mouse_vertical_offset"))
            self.y_min = y - math.ceil(settings.get("user.clickless_mouse_radius") * 2)
            self.y_max = y + math.ceil(settings.get("user.clickless_mouse_radius") * 5) 

        if draw_right:
            self.x_min = x - math.ceil(settings.get("user.clickless_mouse_radius") * 2.25) 
            self.x_max = x + self.get_max_horizontal_distance()          
        else:
            self.x_min = x - self.get_max_horizontal_distance()
            self.x_max = x + math.ceil(settings.get("user.clickless_mouse_radius") * 2.25)

        for index, button_label in enumerate(
            self.get_horizontal_button_order()
        ):
            if draw_right:
                x_pos = x + math.ceil(settings.get("user.clickless_mouse_radius") * (2.5 + settings.get("user.clickless_mouse_horizontal_offset") * (index - 1)))
            else:
                x_pos = x - math.ceil(settings.get("user.clickless_mouse_radius") * (2.5 + settings.get("user.clickless_mouse_horizontal_offset") * (index - 1)))
            
            self.button_positions.append(
                dwell_button(
                    x_pos,
                    y_pos,
                    button_label if not is_left_down else "lr",
                )
            )

    def create_panel(self, x, y, is_left_down):
        self.panel_x, self.panel_y = x, y
        screen = ui.screen_containing(x, y)

        # if the screen is cached, it won't always appear over
        # certain windows
        if True:  # screen != self.screen:
            self.screen = screen
            if self.mcanvas:
                self.mcanvas.close()
                self.mcanvas = None
            self.mcanvas = canvas.Canvas.from_screen(self.screen)
        # self.x, self.y = x, y
        self.set_button_positions(x, y, is_left_down)

    def clear_button_positions(self):
        self.button_positions = []

    def is_outside_panel(self, x, y):
        return x > self.x_max or x < self.x_min or y > self.y_max or y < self.y_min

    def find_hit(self, x, y, now):
        item_hit = None
        for b in self.button_positions:
            if (x <= b.x + settings.get("user.clickless_mouse_radius") and b.x - settings.get("user.clickless_mouse_radius") <= x) and (
                y <= b.y + settings.get("user.clickless_mouse_radius") and b.y - settings.get("user.clickless_mouse_radius") <= y
            ):
                b.hit_check(True)
                self.last_time = now
                item_hit = b
            else:
                b.hit_check(False)
        return item_hit

    def draw(self, canvas):
        self.draw_options(canvas, self.panel_x, self.panel_y)

    def draw_options(self, canvas, x, y):
        paint = canvas.paint
        paint.color = "ff0000dd"
        paint.style = paint.Style.FILL
        # print("{},{}".format(self.x, self.y))
        # print(canvas.rect)
        paint.stroke_width = settings.get("user.clickless_mouse_stroke_width")
        canvas.draw_line(x - settings.get("user.clickless_mouse_radius"), y, x + settings.get("user.clickless_mouse_radius"), y)
        canvas.draw_line(x, y - settings.get("user.clickless_mouse_radius"), x, y + settings.get("user.clickless_mouse_radius"))

        for b in self.button_positions:
            # draw outer circle
            paint.color = "ffffffaa"
            paint.style = paint.Style.STROKE
            canvas.draw_circle(b.x, b.y, settings.get("user.clickless_mouse_radius") + 1)

            # draw inner circle
            paint.color = "000000AA"
            paint.style = paint.Style.FILL
            canvas.draw_circle(b.x, b.y, settings.get("user.clickless_mouse_radius"))

            # draw hit circle
            if b.last_hit_time:
                paint.color = "00FF00"
                paint.style = paint.Style.FILL

                _radius = min(
                    math.ceil(
                        settings.get("user.clickless_mouse_radius")
                        * (time.perf_counter() - b.last_hit_time)
                        / settings.get("user.clickless_mouse_dwell_time")
                    ),
                    settings.get("user.clickless_mouse_radius"),
                )
                canvas.draw_circle(b.x, b.y, _radius)

            canvas.paint.text_align = canvas.paint.TextAlign.CENTER
            text_string = b.action
            paint.textsize = settings.get("user.clickless_mouse_radius")
            paint.color = "ffffffff"

            canvas.draw_text(text_string, b.x, b.y)
