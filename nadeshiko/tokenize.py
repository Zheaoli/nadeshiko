import string
from typing import Optional

from nadeshiko.helper import error_message
from nadeshiko.token import TokenType, Token, new_token, equal
from nadeshiko.utils import Peekable


def get_punctuator_length(expression: str) -> int:
    if (
        expression.startswith("==")
        or expression.startswith("!=")
        or expression.startswith("<=")
        or expression.startswith(">=")
    ):
        return 2
    return 1 if expression[0] in string.printable else 0


def is_keyword(token: Token) -> bool:
    keywords = {"return", "if", "else", "while", "for", "int", "sizeof", "char"}
    if token.expression in keywords:
        return True
    return False


def convert_keyword(tokens: list[Optional[Token]]) -> None:
    for token in tokens:
        if is_keyword(token):
            token.type = TokenType.Keyword


def tokenize(expression: str) -> Peekable[Optional[Token]]:
    index = 0
    tokens = []
    while index < len(expression):
        if expression[index] == " ":
            index += 1
            continue
        if expression[index].isdigit():
            current = new_token(TokenType.Number, index, index)
            tokens.append(current)
            temp = []
            while index < len(expression) and expression[index].isdigit():
                temp.append(expression[index])
                index += 1
            current.value = int("".join(temp))
            current.length = index - current.location
            current.expression = expression[
                current.location : current.location + current.length
            ]
            current.original_expression = expression
            continue
        if expression[index].isalpha():
            end = index
            while expression[end].isalnum() or expression[end] == "_":
                end += 1
            current = new_token(TokenType.Identifier, index, end)
            tokens.append(current)
            current.expression = expression[index:end]
            index = end
            continue
        if (length := get_punctuator_length(expression[index:])) >= 1:
            current = new_token(TokenType.Punctuator, index, index + length)
            tokens.append(current)
            current.expression = expression[
                current.location : current.location + current.length
            ]
            current.original_expression = expression
            index += length
            continue
        print(error_message(expression, index, "invalid token"))
        exit(1)
    tokens.append(new_token(TokenType.EOF, index, index))
    convert_keyword(tokens)
    return Peekable(tokens)


def consume(tokens: Peekable[Optional[Token]], expression: str) -> bool:
    if equal(tokens.peek(), expression):
        next(tokens)
        return True
    return False
