"""ICT killzones and macro windows, in New York time. Edit these lists to change the windows."""
from dataclasses import dataclass
from datetime import time


@dataclass(frozen=True)
class Window:
    name: str
    start: time
    end: time  # time(0, 0) as an end means midnight

    def contains(self, moment: time) -> bool:
        if self.end == time(0, 0):
            return moment >= self.start
        return self.start <= moment < self.end

    def to_dict(self):
        return {"name": self.name, "start": self.start.strftime("%H:%M"), "end": self.end.strftime("%H:%M")}


KILLZONES = [
    Window("Asia", time(20, 0), time(0, 0)),
    Window("London", time(2, 0), time(5, 0)),
    Window("NY AM", time(8, 30), time(11, 0)),
    Window("NY PM", time(13, 30), time(16, 0)),
]

MACROS = [
    Window("Macro", time(2, 33), time(3, 0)),
    Window("Macro", time(4, 3), time(4, 30)),
    Window("Macro", time(8, 50), time(9, 10)),
    Window("Macro", time(9, 50), time(10, 10)),
    Window("Macro", time(10, 50), time(11, 10)),
    Window("Macro", time(11, 50), time(12, 10)),
    Window("Macro", time(13, 10), time(13, 40)),
    Window("Macro", time(15, 15), time(15, 45)),
]


def sessions_config():
    """Window definitions for the frontend clock, so they live in one place."""
    return {
        "killzones": [window.to_dict() for window in KILLZONES],
        "macros": [window.to_dict() for window in MACROS],
    }
