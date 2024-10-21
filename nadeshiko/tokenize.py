import string
from typing import Optional

from nadeshiko.helper import error_message
from nadeshiko.token import TokenType, Token, new_token, equal
from nadeshiko.type import array_of, TYPE_CHAR
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


def read_escape_char(expression: str, index: int) -> tuple[str, int]:
    if ord("0") <= ord(expression[index]) <= ord("7"):
        value = ord(expression[index]) - ord("0")
        index += 1
        if ord("0") <= ord(expression[index]) <= ord("7"):
            value = value * 8 + ord(expression[index]) - ord("0")
            index += 1
            if ord("0") <= ord(expression[index]) <= ord("7"):
                value = value * 8 + ord(expression[index]) - ord("0")
                index += 1
        return chr(value), 3
    match expression[index]:
        case "a":
            return "\a", 1
        case "b":
            return "\b", 1
        case "f":
            return "\f", 1
        case "n":
            return "\n", 1
        case "r":
            return "\r", 1
        case "t":
            return "\t", 1
        case "v":
            return "\v", 1
        case "e":
            return chr(27), 1
        case _:
            return expression[index], 1


def read_string_literal(expression: str, index: int) -> tuple[Token, int]:
    end = -1
    i = index + 1
    while i <= len(expression):
        if expression[i] == '"':
            end = i
            break
        if expression[i] == "\0" or expression[i] == "\n":
            print(error_message(expression, index, "unterminated string"))
            exit(1)
        if expression[i] == "\\":
            i += 1
        i += 1
    length = 0
    results = []
    i = index + 1
    while i < end:
        if expression[i] != '"':
            if expression[i] == "\\":
                value, offset = read_escape_char(expression, i + 1)
                results.append(value)
                i += offset
                length += 1
            else:
                results.append(expression[i])
                length += 1
        i += 1
    str_value = "".join(results)

    token = new_token(TokenType.STRING, index, end + 1)
    token.str_type = array_of(TYPE_CHAR, length + 1)
    token.str_value = str_value
    return token, end + 1


def is_keyword(token: Token) -> bool:
    keywords = {"return", "if", "else", "while", "for", "int", "sizeof", "char"}
    if token.expression in keywords:
        return True
    return False


def convert_keyword(tokens: list[Optional[Token]]) -> None:
    for token in tokens:
        if is_keyword(token):
            token.kind = TokenType.Keyword


def tokenize(expression: str) -> Peekable[Optional[Token]]:
    index = 0
    tokens = []
    while index < len(expression):
        if expression[index] == " ":
            index += 1
            continue
        if expression[index] == '"':
            token, index = read_string_literal(expression, index)
            tokens.append(token)
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
