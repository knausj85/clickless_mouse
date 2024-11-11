import time


class dwell_button:
    def __init__(self, x, y, action="l"):
        self.x = x
        self.y = y
        self.hit = False
        self.action = action
        self.last_hit_time = None

    def hit_check(self, hit):
        if hit:
            if not self.last_hit_time:
                self.last_hit_time = time.perf_counter()
        else:
            hit = False
            self.last_hit_time = None

        self.hit = hit

