# Last Seed - a winding road described by distance along it, using only the Python standard library.
#
# Purpose: the greybox levels run in a straight line along X. This bends that line. A point on the road is written as
# (s, d): s is the distance along the road, and d is the distance to its right. Distances along the road never change,
# so a jump or a puzzle laid out in the straight greybox still measures the same after bending.
# Run "python ls_curved_route.py" to run its self-check outside Unreal.

import math


class CurvedRoad:
    def __init__(self, length, bends, step=25.0):
        """bends is a list of (s_start, s_end, degrees). Positive turns right, and the road is straight between bends."""
        self.length = length
        self.step = step
        self.headings = []
        self.xs = []
        self.ys = []
        heading = 0.0
        x = y = 0.0
        for index in range(int(length / step) + 2):
            s = index * step
            self.xs.append(x)
            self.ys.append(y)
            self.headings.append(heading)
            turn = 0.0
            for s0, s1, degrees in bends:
                overlap = max(0.0, min(s + step, s1) - max(s, s0))
                turn += math.radians(degrees) * overlap / (s1 - s0)
            # Half the turn before moving and half after keeps the arcs accurate at any step size.
            heading += turn / 2.0
            x += math.cos(heading) * step
            y += math.sin(heading) * step
            heading += turn / 2.0

        # A coarse grid of road samples makes finding the nearest point fast. The terrain asks for it tens of thousands of times.
        self.cell = 1500.0
        self.grid = {}
        self.coarse = list(range(0, len(self.xs), 40))
        for index in range(0, len(self.xs), 4):
            self.grid.setdefault(self._cell_of(self.xs[index], self.ys[index]), []).append(index)

    def _cell_of(self, x, y):
        return int(math.floor(x / self.cell)), int(math.floor(y / self.cell))

    def _index(self, s):
        return min(max(s / self.step, 0.0), len(self.xs) - 1.001)

    def heading(self, s):
        index = self._index(s)
        low = int(index)
        return self.headings[low] + (self.headings[low + 1] - self.headings[low]) * (index - low)

    def yaw(self, s):
        return math.degrees(self.heading(s))

    def point(self, s, d=0.0):
        """World X and Y. Past either end the road carries on in a straight line."""
        index = self._index(s)
        low = int(index)
        t = index - low
        x = self.xs[low] + (self.xs[low + 1] - self.xs[low]) * t
        y = self.ys[low] + (self.ys[low + 1] - self.ys[low]) * t
        heading = self.heading(s)
        extra = s - index * self.step
        x += math.cos(heading) * extra
        y += math.sin(heading) * extra
        return x - math.sin(heading) * d, y + math.cos(heading) * d

    def project(self, x, y):
        """The (s, d) of the nearest road point. s can fall outside the road, which tells the caller how far past the end it is."""
        cell_x, cell_y = self._cell_of(x, y)
        candidates = []
        for offset_x in (-1, 0, 1):
            for offset_y in (-1, 0, 1):
                candidates += self.grid.get((cell_x + offset_x, cell_y + offset_y), [])
        best = min(candidates or self.coarse, key=lambda i: (self.xs[i] - x) ** 2 + (self.ys[i] - y) ** 2)
        # The grid samples are 100 cm apart, or 1000 for far points, so this searches between them.
        reach = 4 if candidates else 40
        first, last = max(best - reach, 0), min(best + reach, len(self.xs) - 1)
        best = min(range(first, last + 1), key=lambda i: (self.xs[i] - x) ** 2 + (self.ys[i] - y) ** 2)
        heading = self.headings[best]
        dx, dy = x - self.xs[best], y - self.ys[best]
        along = dx * math.cos(heading) + dy * math.sin(heading)
        side = -dx * math.sin(heading) + dy * math.cos(heading)
        return best * self.step + along, side


def self_check():
    road = CurvedRoad(4000.0, [(500.0, 2000.0, 90.0)])
    assert abs(road.yaw(3000.0) - 90.0) < 0.01
    x, y = road.point(0.0, 100.0)
    assert abs(x) < 0.01 and abs(y - 100.0) < 0.01, "positive d is the right-hand side"
    # A right-hand arc of 90 degrees over 1500 cm has this exact end point.
    radius = 1500.0 / (math.pi / 2.0)
    x, y = road.point(2000.0)
    assert abs(x - (500.0 + radius)) < 2.0 and abs(y - radius) < 2.0, (x, y, radius)
    for s, d in ((100.0, 50.0), (1200.0, -300.0), (1200.0, 200.0), (3000.0, 400.0), (4500.0, 100.0), (-300.0, -200.0)):
        found_s, found_d = road.project(*road.point(s, d))
        assert abs(found_s - s) < 8.0 and abs(found_d - d) < 8.0, (s, d, found_s, found_d)
    print("Last Seed curved road: self-check passed")


if __name__ == "__main__":
    self_check()
