from dataclasses import dataclass
from typing import Literal


@dataclass
class Dependency:
    key: str
    type: Literal["header", "library"]
    dest: str
