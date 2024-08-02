import string
from typing import Optional

from nadeshiko.helper import error_message
from nadeshiko.token import TokenType, Token, new_token


def get_punctuator_length(expression: str) -> int:
    if (
        expression.startswith("==")
        or expression.startswith("!=")
        or expression.startswith("<=")
        or expression.startswith(">=")
    ):
        return 2
    return 1 if expression[0] in string.printable else 0


def tokenize(expression: str) -> Optional[Token]:
    head = Token()
    current: Token = head
    index = 0
    while index < len(expression):
        if expression[index] == " ":
            index += 1
            continue
        if expression[index].isdigit():
            current.next_token = new_token(TokenType.Number, index, index)
            current = current.next_token
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
            current.next_token = new_token(TokenType.Identifier, index, end)
            current = current.next_token
            current.expression = expression[index:end]
            index = end
            continue
        if (length := get_punctuator_length(expression[index:])) >= 1:
            current.next_token = new_token(TokenType.Punctuator, index, index + length)
            current = current.next_token
            current.expression = expression[
                current.location : current.location + current.length
            ]
            current.original_expression = expression
            index += length
            continue
        print(error_message(expression, index, "invalid token"))
        exit(1)
    current.next_token = new_token(TokenType.EOF, index, index)
    return head.next_token
