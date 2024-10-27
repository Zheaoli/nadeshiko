from dataclasses import dataclass
from enum import IntEnum
from typing import Optional

from nadeshiko.helper import error_message
from nadeshiko.type import Type


class TokenType(IntEnum):
    Punctuator = 1
    Number = 2
    EOF = 3
    Identifier = 4
    Keyword = 5
    STRING = 6


@dataclass
class Token:
    kind: Optional[TokenType] = None
    value: Optional[int] = None
    location: Optional[int] = None
    length: Optional[int] = None
    expression: Optional[str] = None
    original_expression: Optional[str] = None
    str_value: Optional[str] = None
    str_type: Optional["Type"] = None
    line_number: int = 0


def new_token(
    token_type: Optional[TokenType] = None, start: int = 0, end: int = 0
) -> Token:
    return Token(token_type, None, start, end - start, None, None)


def get_number(token: Token) -> int:
    if token.kind != TokenType.Number:
        print(
            error_message(token.original_expression, token.location, "expected number")
        )
        exit(1)
    return token.value


def equal(token: Token, expression: str) -> bool:
    return token.expression == expression


def skip(token: Token, expression: str) -> None:
    assert token.expression == expression
