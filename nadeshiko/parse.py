from typing import Optional

from nadeshiko.helper import error_message
from nadeshiko.node import (
    Node,
    new_binary,
    NodeType,
    new_unary,
    new_number,
    new_var_node, Obj, new_lvar, Function, new_node,
)
from nadeshiko.token import Token, TokenType, equal, skip


def parse_stmt(token: Token) -> Optional["Function"]:
    token = skip(token, "{")
    local_objs: list[Optional["Obj"]] = [None]
    _, node = convert_compound_stmt(token, local_objs)
    local_objs.pop(0)
    return Function(node, local_objs, 0)


def parse_stmt_return(token: Token, local_objs: list[Optional["Obj"]]) -> tuple[Optional[Token], Optional[Node]]:
    if equal(token, "return"):
        token, node = expression_parse(token.next_token, local_objs)
        node = new_unary(NodeType.Return, node)
        token = skip(token, ";")
        return token, node
    if equal(token, "if"):
        node = new_node(NodeType.If)
        token = skip(token.next_token, "(")
        token, node.condition = expression_parse(token, local_objs)
        token = skip(token, ")")
        token, node.then = parse_stmt_return(token, local_objs)
        if equal(token, "else"):
            token, node.els = parse_stmt_return(token.next_token, local_objs)
        return token, node
    if equal(token, "for"):
        node = new_node(NodeType.ForStmt)
        token = skip(token.next_token, "(")
        token, node.init = expression_parse_stmt(token, local_objs)
        if not equal(token, ";"):
            token, node.condition = expression_parse(token, local_objs)
        token = skip(token, ";")
        if not equal(token, ")"):
            token, node.inc = expression_parse(token, local_objs)
        token = skip(token, ")")
        token, node.then = parse_stmt_return(token, local_objs)
        return token, node

    if equal(token, "{"):
        return convert_compound_stmt(token.next_token, local_objs)
    return expression_parse_stmt(token, local_objs)


def expression_parse_stmt(token: Token, local_objs: list[Optional["Obj"]]) -> tuple[Optional[Token], Optional[Node]]:
    if equal(token, ";"):
        return token.next_token, new_node(NodeType.Block)
    token, node = expression_parse(token, local_objs)
    node = new_unary(NodeType.ExpressionStmt, node)
    token = skip(token, ";")
    return token, node


def expression_parse(token: Token, local_objs: list[Optional["Obj"]]) -> tuple[Optional[Token], Optional[Node]]:
    return convert_assign_token(token, local_objs)


def convert_compound_stmt(token: Token, local_objs: list[Optional["Obj"]]) -> tuple[Optional[Token], Optional[Node]]:
    head = new_node(NodeType.Block)
    current = head
    while not equal(token, "}"):
        token, node = parse_stmt_return(token, local_objs)
        current.next_node = node
        current = node
    node = new_node(NodeType.Block)
    node.body = head.next_node
    return token.next_token, node


def convert_relational_token(token: Token, local_objs: list[Optional["Obj"]]) -> tuple[Optional[Token], Optional[Node]]:
    token, node = convert_add_token(token, local_objs)
    while True:
        if equal(token, "<") or equal(token, ">"):
            next_token, next_node = convert_add_token(token.next_token, local_objs)
            left_node = node if equal(token, "<") else next_node
            right_node = next_node if equal(token, "<") else node
            node = new_binary(NodeType.Less, left_node, right_node)
            token = next_token
            continue
        if equal(token, "<=") or equal(token, ">="):
            next_token, next_node = convert_add_token(token.next_token, local_objs)
            left_node = node if equal(token, "<=") else next_node
            right_node = next_node if equal(token, "<=") else node
            node = new_binary(NodeType.LessEqual, left_node, right_node)
            token = next_token
            continue
        return token, node


def convert_assign_token(token: Token, local_objs: list[Optional["Obj"]]) -> tuple[Optional[Token], Optional[Node]]:
    token, node = convert_equality_token(token, local_objs)
    if equal(token, "="):
        next_token, next_node = convert_assign_token(token.next_token, local_objs)
        node = new_binary(NodeType.Assign, node, next_node)
        token = next_token
    return token, node


def convert_equality_token(token: Token, local_objs: list[Optional["Obj"]]) -> tuple[Optional[Token], Optional[Node]]:
    token, node = convert_relational_token(token, local_objs)
    while True:
        if equal(token, "=="):
            token, next_node = convert_relational_token(token.next_token, local_objs)
            node = new_binary(NodeType.Equal, node, next_node)
            continue
        if equal(token, "!="):
            token, next_node = convert_relational_token(token.next_token, local_objs)
            node = new_binary(NodeType.NotEqual, node, next_node)
            continue
        return token, node


def convert_add_token(token: Token, local_objs: list[Optional["Obj"]]) -> tuple[Optional[Token], Optional[Node]]:
    token, node = convert_mul_token(token, local_objs)
    while True:
        if equal(token, "+"):
            next_token, next_node = convert_mul_token(token.next_token, local_objs)
            node = new_binary(NodeType.Add, node, next_node)
            token = next_token
            continue
        if equal(token, "-"):
            next_token, next_node = convert_mul_token(token.next_token, local_objs)
            node = new_binary(NodeType.Sub, node, next_node)
            token = next_token
            continue
        return token, node


def convert_unary_token(token: Token, local_objs: list[Optional["Obj"]]) -> tuple[Optional[Token], Optional[Node]]:
    if equal(token, "+"):
        return convert_unary_token(token.next_token, local_objs)
    if equal(token, "-"):
        token, node = convert_unary_token(token.next_token, local_objs)
        node = new_unary(NodeType.Neg, node)
        return token, node
    return primary_token(token, local_objs)


def convert_mul_token(token: Token, local_objs: list[Optional["Obj"]]) -> tuple[Optional[Token], Optional[Node]]:
    token, node = convert_unary_token(token, local_objs)
    while True:
        if equal(token, "*"):
            next_token, next_node = primary_token(token.next_token, local_objs)
            node = new_binary(NodeType.Mul, node, next_node)
            token = next_token
            continue
        if equal(token, "/"):
            next_token, next_node = primary_token(token.next_token, local_objs)
            node = new_binary(NodeType.Div, node, next_node)
            token = next_token
            continue
        return token, node


def primary_token(token: Token, local_objs: list[Optional["Obj"]]) -> tuple[Optional[Token], Optional[Node]]:
    if equal(token, "("):
        next_token, node = expression_parse(token.next_token, local_objs)
        return skip(next_token, ")"), node
    if token.type == TokenType.Number:
        return token.next_token, new_number(token.value)
    if token.type == TokenType.Identifier:
        obj = search_obj(token.expression, local_objs)
        if not obj:
            obj = new_lvar(token.expression, local_objs[-1])
            local_objs.append(obj)
        return token.next_token, new_var_node(obj)
    print(error_message(token.expression, token.location, "expected an expression"))
    exit(1)


def search_obj(obj: str, local_objs: list[Optional["Obj"]]) -> Optional[Obj]:
    for local_obj in local_objs:
        if local_obj and local_obj.name == obj:
            return local_obj
    return None
