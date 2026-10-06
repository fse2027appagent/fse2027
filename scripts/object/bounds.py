class Bounds:

    def __init__(self, bounds_list = None):
        if bounds_list is None:
            bounds_list = [0, 0, 0, 0]
        if len(bounds_list) != 4:
            pass
        else:
            self.x1 = int(bounds_list[0])
            self.y1 = int(bounds_list[1])
            self.x2 = int(bounds_list[2])
            self.y2 = int(bounds_list[3])

    def combine(self, other):
        if isinstance(other, Bounds):
            self.x1 = min(self.x1, other.x1)
            self.y1 = min(self.y1, other.y1)
            self.x2 = max(self.x2, other.x2)
            self.y2 = max(self.y2, other.y2)

    def to_list(self):
        return [
            self.x1,
            self.y1,
            self.x2,
            self.y2
        ]
