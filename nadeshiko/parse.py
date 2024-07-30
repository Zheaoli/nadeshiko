from typing import Optional

from nadeshiko.helper import error_message
from nadeshiko.node import Node, new_binary, NodeType, new_unary, new_number
from nadeshiko.token import Token, TokenType, equal, skip


def parse(token: Token) -> tuple[Optional[Token], Optional[Node]]:
    return convert_equality_token(token)


def convert_relational_token(token: Token) -> tuple[Optional[Token], Optional[Node]]:
    token, node = convert_add_token(token)
    while True:
        if equal(token, "<") or equal(token, ">"):
            next_token, next_node = convert_add_token(token.next_token)
            left_node = node if equal(token, "<") else next_node
            right_node = next_node if equal(token, "<") else node
            node = new_binary(NodeType.Less, left_node, right_node)
            token = next_token
            continue
        if equal(token, "<=") or equal(token, ">="):
            next_token, next_node = convert_add_token(token.next_token)
            left_node = node if equal(token, "<=") else next_node
            right_node = next_node if equal(token, "<=") else node
            node = new_binary(NodeType.LessEqual, left_node, right_node)
            token = next_token
            continue
        return token, node


def convert_equality_token(token: Token) -> tuple[Optional[Token], Optional[Node]]:
    token, node = convert_relational_token(token)
    while True:
        if equal(token, "=="):
            token, next_node = convert_relational_token(token.next_token)
            node = new_binary(NodeType.Equal, node, next_node)
            continue
        if equal(token, "!="):
            token, next_node = convert_relational_token(token.next_token)
            node = new_binary(NodeType.NotEqual, node, next_node)
            continue
        return token, node


def convert_add_token(token: Token) -> tuple[Optional[Token], Optional[Node]]:
    token, node = convert_mul_token(token)
    while True:
        if equal(token, "+"):
            next_token, next_node = convert_mul_token(token.next_token)
            node = new_binary(NodeType.Add, node, next_node)
            token = next_token
            continue
        if equal(token, "-"):
            next_token, next_node = convert_mul_token(token.next_token)
            node = new_binary(NodeType.Sub, node, next_node)
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
            next_token, next_node = primary_token(token.next_token)
            node = new_binary(NodeType.Mul, node, next_node)
            token = next_token
            continue
        if equal(token, "/"):
            next_token, next_node = primary_token(token.next_token)
            node = new_binary(NodeType.Div, node, next_node)
            token = next_token
            continue
        return token, node


def primary_token(token: Token) -> tuple[Optional[Token], Optional[Node]]:
    if equal(token, "("):
        next_token, node = parse(token.next_token)
        return skip(next_token, ")"), node
    if token.type == TokenType.Number:
        return token.next_token, new_number(token.value)
    print(error_message(token.expression, token.location, "expected an expression"))
    exit(1)
