from __future__ import annotations

import math


class OccupancyScale:
    
    MIN_INDEX: int = 1
    MAX_INDEX: int = 10

    def to_index(self, visitors: int, capacity: int) -> int:
        if capacity < 1:
            raise ValueError("Вместимость зала должна быть не меньше 1")
        share = max(visitors, 0) / capacity
        raw = math.ceil(share * self.MAX_INDEX)
        return min(max(raw, self.MIN_INDEX), self.MAX_INDEX)
