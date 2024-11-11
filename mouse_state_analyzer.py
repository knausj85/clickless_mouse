from talon import ctrl
from .constants import *

import math, time

class mouse_state_analyzer:
    def __init__(self):
        self.x, self.y = ctrl.mouse_pos()
        self._dwell_x, self._dwell_y = ctrl.mouse_pos()
        self.state = STATE_MOUSE_IDLE
        self.last_stopped_time = None
        self.standstill_delay = 0
        self.standstill_detection = STANDSTILL_DETECT_ONLY_IF_MOUSE_BUTTONS_UP

        # after moving the mouse to perform an action,
        # avoid a state change in the first update.
        # this prevents an unnecessary re-display
        self.suppress_next_update = False

    def set_standstill_delay(self, delay):
        self.standstill_delay = delay

    def set_standstill_detection(self, detection):
        self.standstill_detection = detection

    def enable(self):
        self.x, self.y = ctrl.mouse_pos()
        self._dwell_x, self._dwell_y = ctrl.mouse_pos()

    def is_left_down(self):
        return left_mouse_button_index in ctrl.mouse_buttons_down()

    def are_any_buttons_down(self):
        return len(ctrl.mouse_buttons_down()) > 0
    
    def determine_new_state(self) -> int:
        # print("update")
        x, y = ctrl.mouse_pos()
        now = time.perf_counter()
        update_last_xy = False
        new_state = self.state
        same_position = x == self.x and y == self.y

        # print("({},{})".format(x, y))
        if self.state == STATE_MOUSE_IDLE:
            # print("idle")
            if self.suppress_next_update:
                self.suppress_next_update = False
                update_last_xy = True
            elif math.fabs(self.x - x) > 1 or math.fabs(self.y - y) > 1:
                update_last_xy = True
                new_state = STATE_MOUSE_MOVING
            self.last_stopped_time = None

        elif self.state == STATE_MOUSE_MOVING:
            # print("moving")

            if same_position:
                self.last_stopped_time = now
                new_state = STATE_MOUSE_STOPPED
            else:
                self.last_stopped_time = None

            update_last_xy = True

        elif self.state == STATE_MOUSE_STOPPED:
            # print("stopped")

            if not self.mouse_standstill_detection_wanted():
                new_state = STATE_MOUSE_IDLE
                update_last_xy = True

            elif same_position:
                if now - self.last_stopped_time >= self.standstill_delay:
                    # self.last_time = now
                    # self._dwell_x, self._dwell_y = ctrl.mouse_pos()
                    update_last_xy = True
                    new_state = STATE_MOUSE_STANDSTILL
            else:
                self.last_stopped_time = None
                update_last_xy = True
                new_state = STATE_MOUSE_MOVING

        elif self.state == STATE_MOUSE_STANDSTILL:
            # print("standstill")

            if not same_position:
                self.last_stopped_time = None
                update_last_xy = True
                new_state = STATE_MOUSE_MOVING

        elif self.state == STATE_DISPLAYING_OPTIONS:
            # there is nothing we can check in the STATE_DISPLAYING_OPTIONS state within this class... 
            # it's all up to the caller of this method and the concrete clicker class.
            
            # for example, the two stage clicker class checks to see the mouse position relative to the panel, and if
            # the mouse moves outside of the dwell panel, then it specifies a new state of STATE_MOUSE_IDLE
            pass
            
        if update_last_xy:
            self.do_update_last_xy()

        return new_state

    def do_update_last_xy(self):
        self.prev_x, self.prev_y = self.x, self.y
        self.x, self.y = ctrl.mouse_pos()

    def mouse_standstill_detection_wanted(self):
        if self.standstill_detection == STANDSTILL_DETECT_ONLY_IF_MOUSE_BUTTONS_UP:
            # if the user is manually pressing one or more of the mouse buttons,
            # then it seems unlikely that when they release the button, that they would want us to automatically 
            # perform a click when they let go
            result = not self.are_any_buttons_down()
        else:
            # (self.standstill_detection == STANDSTILL_DETECT_ALWAYS)
            # an exception is when we are using the single_stage clicker and it is performing a drag.
            # at this time we still need to detect a standstill as that is the signal to terminate the drag.
            result = True
        return result
