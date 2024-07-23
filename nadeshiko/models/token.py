from dataclasses import dataclass
from enum import IntEnum
from typing import Optional


class TokenType(IntEnum):
    Punctuator = 1
    Number = 2
    EOF = 3


@dataclass
class Token:
    type: Optional[TokenType] = None
    next_token: Optional["Token"] = None
    value: Optional[int] = None
    location: Optional[int] = None
    length: Optional[int] = None
    expression: Optional[str] = None
    original_expression: Optional[str] = None
