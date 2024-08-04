from dataclasses import dataclass
from enum import IntEnum
from typing import Optional

from nadeshiko.helper import error_message


class TokenType(IntEnum):
    Punctuator = 1
    Number = 2
    EOF = 3
    Identifier = 4
    Keyword = 5


@dataclass
class Token:
    type: Optional[TokenType] = None
    next_token: Optional["Token"] = None
    value: Optional[int] = None
    location: Optional[int] = None
    length: Optional[int] = None
    expression: Optional[str] = None
    original_expression: Optional[str] = None


def new_token(
    token_type: Optional[TokenType] = None, start: int = 0, end: int = 0
) -> Token:
    return Token(token_type, None, None, start, end - start, None, None)


def get_number(token: Token) -> int:
    if token.type != TokenType.Number:
        print(
            error_message(token.original_expression, token.location, "expected number")
        )
        exit(1)
    return token.value


def equal(token: Token, expression: str) -> bool:
    return token.expression == expression


def skip(token: Token, expression: str) -> Token:
    assert token.expression == expression
    return token.next_token
