from typing import Optional

import typer

from nadeshiko.models.token import Token, TokenType


def error_message(expression: str, location: int, message: str) -> str:
    messages = [f"{expression}\n",
                f"{' ' * location}^ {message}\n"]
    return "".join(messages)


def new_token(token_type: Optional[TokenType] = None, start: int = 0, end: int = 0) -> Token:
    return Token(token_type, None, None, start, end - start, None, None)


def get_number(token: Token) -> int:
    if token.type != TokenType.Number:
        print(error_message(token.original_expression, token.location, "expected number"))
        exit(1)
    return token.value


def equal(token: Token, expression: str) -> bool:
    return token.expression == expression


def skip(token: Token, expression: str) -> Token:
    assert token.expression == expression
    return token.next_token


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
            current.expression = expression[current.location:current.location + current.length]
            current.original_expression = expression
            continue
        if expression[index] in "+-":
            current.next_token = new_token(TokenType.Punctuator, index, index + 1)
            current = current.next_token
            current.expression = expression[current.location:current.location + current.length]
            current.original_expression = expression
            index += 1
            continue
        print(error_message(expression, index, "invalid token"))
        exit(1)
    current.next_token = new_token(TokenType.EOF, index, index)
    return head.next_token


def main(expression: str):
    output_asm = [f"  .global main\n",
                  f"main:\n"]
    assert len(expression) >= 0
    token = tokenize(expression)
    output_asm.append(f"  mov ${get_number(token)}, %rax\n")
    while token.type != TokenType.EOF:
        match token.expression:
            case "+":
                token = skip(token, "+")
                output_asm.append(f"  add ${get_number(token)}, %rax\n")
            case "-":
                token = skip(token, "-")
                output_asm.append(f"  sub ${get_number(token)}, %rax\n")
            case _:
                token = token.next_token
    output_asm.append(f"  ret\n")

    print("".join(output_asm), flush=True)


if __name__ == '__main__':
    typer.run(main)
