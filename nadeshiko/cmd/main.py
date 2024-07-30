import string
from typing import Optional

import typer

from nadeshiko.models.node import Node, new_number, new_binary, NodeType, new_unary
from nadeshiko.models.token import Token, TokenType

app = typer.Typer()


def error_message(expression: str, location: int, message: str) -> str:
    messages = [f"{expression}\n", f"{' ' * location}^ {message}\n"]
    return "".join(messages)


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


def get_punctuator_length(expression: str) -> int:
    if (
        expression.startswith("==")
        or expression.startswith("!=")
        or expression.startswith("<=")
        or expression.startswith(">=")
    ):
        return 2
    return 1 if expression[0] in string.printable else 0


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
            current.expression = expression[
                current.location : current.location + current.length
            ]
            current.original_expression = expression
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


def convert_token_to_node(token: Token) -> tuple[Optional[Token], Optional[Node]]:
    return convert_equality_to_node(token)


def convert_relational_to_node(token: Token) -> tuple[Optional[Token], Optional[Node]]:
    token, node = convert_add_to_node(token)
    while True:
        if equal(token, "<") or equal(token, ">"):
            next_token, next_node = convert_add_to_node(token.next_token)
            left_node = node if equal(token, "<") else next_node
            right_node = next_node if equal(token, "<") else node
            node = new_binary(NodeType.Less, left_node, right_node)
            token = next_token
            continue
        if equal(token, "<=") or equal(token, ">="):
            next_token, next_node = convert_add_to_node(token.next_token)
            left_node = node if equal(token, "<=") else next_node
            right_node = next_node if equal(token, "<=") else node
            node = new_binary(NodeType.LessEqual, left_node, right_node)
            token = next_token
            continue
        return token, node


def convert_equality_to_node(token: Token) -> tuple[Optional[Token], Optional[Node]]:
    token, node = convert_relational_to_node(token)
    while True:
        if equal(token, "=="):
            token, right_node = convert_relational_to_node(token.next_token)
            node = new_binary(NodeType.Equal, node, right_node)
            continue
        if equal(token, "!="):
            token, right_node = convert_relational_to_node(token.next_token)
            node = new_binary(NodeType.NotEqual, node, right_node)
            continue
        return token, node


def convert_add_to_node(token: Token) -> tuple[Optional[Token], Optional[Node]]:
    token, node = convert_mul_token(token)
    while True:
        if equal(token, "+"):
            next_token, right_node = convert_mul_token(token.next_token)
            node = new_binary(NodeType.Add, node, right_node)
            token = next_token
            continue
        if equal(token, "-"):
            next_token, right_node = convert_mul_token(token.next_token)
            node = new_binary(NodeType.Sub, node, right_node)
            token = next_token
            continue
        return token, node


def convert_unary_token(token: Token) -> tuple[Optional[Token], Optional[Node]]:
    if equal(token, "+"):
        return convert_unary_token(token.next_token)
    if equal(token, "-"):
        token, node = convert_unary_token(token.next_token)
        node = new_unary(node)
        return token, node
    return primary_token(token)


def convert_mul_token(token: Token) -> tuple[Optional[Token], Optional[Node]]:
    token, node = convert_unary_token(token)
    while True:
        if equal(token, "*"):
            next_token, right_node = primary_token(token.next_token)
            node = new_binary(NodeType.Mul, node, right_node)
            token = next_token
            continue
        if equal(token, "/"):
            next_token, right_node = primary_token(token.next_token)
            node = new_binary(NodeType.Div, node, right_node)
            token = next_token
            continue
        return token, node


def primary_token(token: Token) -> tuple[Optional[Token], Optional[Node]]:
    if equal(token, "("):
        next_token, node = convert_token_to_node(token.next_token)
        return skip(next_token, ")"), node
    if token.type == TokenType.Number:
        return token.next_token, new_number(token.value)
    print(error_message(token.expression, token.location, "expected an expression"))
    exit(1)


def generate_asm(node: Node, depth: int) -> (list[str], int):
    result = []
    if not node:
        return result, depth

    def push(depth: int) -> (list[str], depth):
        return ["  push %rax\n"], depth + 1

    def pop(register: str, depth: int) -> (list[str], depth):
        return [f"  pop %{register}\n"], depth - 1

    match node.kind:
        case NodeType.Number:
            result.append(f"  mov ${node.value}, %rax\n")
            return result, depth
        case NodeType.Neg:
            temp_data, depth = generate_asm(node.left, depth)
            result.extend(temp_data)
            result.append(f"  neg %rax\n")
            return result, depth
    temp_data, depth = generate_asm(node.right, depth)
    result.extend(temp_data)
    temp_data, depth = push(depth)
    result.extend(temp_data)
    temp_data, depth = generate_asm(node.left, depth)
    result.extend(temp_data)
    temp_data, depth = pop("rdi", depth)
    result.extend(temp_data)
    match node.kind:
        case NodeType.Add:
            result.append(f"  add %rdi, %rax\n")
            return result, depth
        case NodeType.Sub:
            result.append(f"  sub %rdi, %rax\n")
            return result, depth
        case NodeType.Mul:
            result.append(f"  imul %rdi, %rax\n")
            return result, depth
        case NodeType.Div:
            result.append(f"  cqo\n")
            result.append(f"  div %rdi, %rax\n")
            return result, depth
        case NodeType.Equal | NodeType.NotEqual | NodeType.Less | NodeType.LessEqual:
            result.append(f"  cmp %rdi, %rax\n")
            match node.kind:
                case NodeType.Equal:
                    result.append("  sete %al\n")
                case NodeType.NotEqual:
                    result.append("  setne %al\n")
                case NodeType.Less:
                    result.append("  setl %al\n")
                case NodeType.LessEqual:
                    result.append("  setle %al\n")
            result.append("  movzb %al, %rax\n")
            return result, depth
    raise ValueError("invalid node type")


@app.command(context_settings={"ignore_unknown_options": True})
def main(expression: str):
    output_asm = [f"  .global main\n", f"main:\n"]
    assert len(expression) >= 0
    token = tokenize(expression)
    token, node = convert_token_to_node(token)
    assert token.type == TokenType.EOF
    temp, depth = generate_asm(node, 0)
    assert depth == 0
    output_asm.extend(temp)
    output_asm.append(f"  ret\n")
    print("".join(output_asm), flush=True)


if __name__ == "__main__":
    app()
