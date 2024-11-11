from abc import ABC, abstractmethod
from typing import Tuple

class on_panel_display_result:
    def __init__(self, next_state, update_last_xy, suppress_next_update):
        self.next_state = next_state
        self.update_last_xy = update_last_xy
        self.suppress_next_update = suppress_next_update


class clicker_base(ABC):
    @abstractmethod
    def on_disable(self):
        pass

    def standstill_delay(self) -> int:
        """delay after mouse stops moving before on_standstill should be called"""
        pass

    def set_next_standstill_action(self, action):
        """set the action to be performed when the next standstill occurs"""
        pass

    def on_standstill(self, x, y, is_left_down) -> tuple[int, int]:
        """called when the mouse has stopped for the user defined duration"""
        pass

    def on_movement_restart(self):
        """called when the mouse has started moving again from the stopped state"""
        pass
    
    def on_panel_display(self, x, y) -> on_panel_display_result:
        """called when the mouse has started moving again from the displaying options state"""
        pass
