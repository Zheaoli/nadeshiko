from typing import Optional

from nadeshiko.helper import error_message
from nadeshiko.node import (
    Node,
    new_binary,
    NodeKind,
    new_unary,
    new_number,
    new_var_node,
    Obj,
    new_lvar,
    Function,
    new_node,
    add_type,
)
from nadeshiko.token import TokenType, equal, skip, Token
from nadeshiko.type import is_integer, TYPE_INT
from nadeshiko.utils import Peekable


class Parse:
    tokens: Peekable[Optional[Token]]
    local_objs: list[Optional["Obj"]]

    def __init__(self, tokens: Peekable[Optional[Token]]) -> None:
        self.tokens = tokens
        self.local_objs = [None]

    def parse_stmt(self) -> Optional["Function"]:
        skip(next(self.tokens), "{")
        node = self.convert_compound_stmt()
        self.local_objs.pop(0)
        return Function(node, self.local_objs, 0)

    def parse_stmt_return(self) -> Optional[Node]:
        token = self.tokens.peek()
        if equal(token, "return"):
            next(self.tokens)
            node = self.expression_parse()
            node = new_unary(NodeKind.Return, node, token)
            skip(next(self.tokens), ";")
            return node
        if equal(token, "if"):
            node = new_node(NodeKind.If, token)
            next(self.tokens)
            skip(next(self.tokens), "(")
            node.condition = self.expression_parse()
            skip(next(self.tokens), ")")
            node.then = self.parse_stmt_return()
            if equal(self.tokens.peek(), "else"):
                next(self.tokens)
                node.els = self.parse_stmt_return()
            return node
        if equal(token, "while"):
            node = new_node(NodeKind.ForStmt, token)
            next(self.tokens)
            skip(next(self.tokens), "(")
            node.condition = self.expression_parse()
            skip(next(self.tokens), ")")
            node.then = self.parse_stmt_return()
            return node
        if equal(token, "for"):
            node = new_node(NodeKind.ForStmt, token)
            next(self.tokens)
            skip(next(self.tokens), "(")
            node.init = self.expression_parse_stmt()
            if not equal(self.tokens.peek(), ";"):
                node.condition = self.expression_parse()
            skip(next(self.tokens), ";")
            if not equal(self.tokens.peek(), ")"):
                node.inc = self.expression_parse()
            skip(next(self.tokens), ")")
            node.then = self.parse_stmt_return()
            return node

        if equal(token, "{"):
            next(self.tokens)
            return self.convert_compound_stmt()
        return self.expression_parse_stmt()

    def expression_parse_stmt(self) -> Optional[Node]:
        token = self.tokens.peek()
        if equal(token, ";"):
            next(self.tokens)
            return new_node(NodeKind.Block, token)
        node = self.expression_parse()
        node = new_unary(NodeKind.ExpressionStmt, node, token)
        skip(next(self.tokens), ";")
        return node

    def expression_parse(self) -> Optional[Node]:
        return self.convert_assign_token()

    def convert_compound_stmt(self) -> Optional[Node]:
        head = new_node(NodeKind.Block, self.tokens.peek())
        current = head
        while not equal(self.tokens.peek(), "}"):
            node = self.parse_stmt_return()
            current.next_node = node
            current = node
        node = new_node(NodeKind.Block, self.tokens.peek())
        node.body = head.next_node
        next(self.tokens)
        return node

    def convert_relational_token(self) -> Optional[Node]:
        node = self.convert_add_token()
        while True:
            token = self.tokens.peek()
            if equal(token, "<") or equal(token, ">"):
                next(self.tokens)
                next_node = self.convert_add_token()
                left_node = node if equal(token, "<") else next_node
                right_node = next_node if equal(token, "<") else node
                node = new_binary(NodeKind.Less, left_node, right_node, token)
                continue
            if equal(token, "<=") or equal(token, ">="):
                next(self.tokens)
                next_node = self.convert_add_token()
                left_node = node if equal(token, "<=") else next_node
                right_node = next_node if equal(token, "<=") else node
                node = new_binary(NodeKind.LessEqual, left_node, right_node, token)
                continue
            return node

    def convert_assign_token(self) -> Optional[Node]:
        node = self.convert_equality_token()
        if equal(self.tokens.peek(), "="):
            token = next(self.tokens)
            next_node = self.convert_assign_token()
            node = new_binary(NodeKind.Assign, node, next_node, token)
        return node

    def convert_equality_token(self) -> Optional[Node]:
        node = self.convert_relational_token()
        while True:
            token = self.tokens.peek()
            if equal(token, "=="):
                next(self.tokens)
                next_node = self.convert_relational_token()
                node = new_binary(NodeKind.Equal, node, next_node, token)
                continue
            if equal(token, "!="):
                next(self.tokens)
                next_node = self.convert_relational_token()
                node = new_binary(NodeKind.NotEqual, node, next_node, token)
                continue
            return node

    def convert_add_token(self) -> Optional[Node]:
        node = self.convert_mul_token()
        while True:
            token = self.tokens.peek()
            if equal(token, "+"):
                next(self.tokens)
                next_node = self.convert_mul_token()
                node = self.new_add(node, next_node, token)
                continue
            if equal(token, "-"):
                next(self.tokens)
                next_node = self.convert_mul_token()
                node = self.new_sub(node, next_node, token)
                continue
            return node

    def convert_unary_token(self) -> Optional[Node]:
        token = self.tokens.peek()
        if equal(token, "+"):
            next(self.tokens)
            return self.convert_unary_token()
        if equal(token, "-"):
            next(self.tokens)
            node = self.convert_unary_token()
            node = new_unary(NodeKind.Neg, node, token)
            return node
        if equal(token, "&"):
            next(self.tokens)
            node = self.primary_token()
            node = new_unary(NodeKind.Addr, node, token)
            return node
        if equal(token, "*"):
            next(self.tokens)
            node = self.convert_unary_token()
            node = new_unary(NodeKind.Deref, node, token)
            return node
        return self.primary_token()

    def convert_mul_token(self) -> Optional[Node]:
        node = self.convert_unary_token()
        while True:
            token = self.tokens.peek()
            if equal(token, "*"):
                next(self.tokens)
                next_node = self.primary_token()
                node = new_binary(NodeKind.Mul, node, next_node, token)
                continue
            if equal(token, "/"):
                next(self.tokens)
                next_node = self.primary_token()
                node = new_binary(NodeKind.Div, node, next_node, token)
                continue
            return node

    def primary_token(self) -> Optional[Node]:
        token = self.tokens.peek()
        if equal(token, "("):
            next(self.tokens)
            next_node = self.expression_parse()
            skip(next(self.tokens), ")")
            return next_node
        if token.type == TokenType.Number:
            next(self.tokens)
            return new_number(token.value, token)
        if token.type == TokenType.Identifier:
            next(self.tokens)
            obj = search_obj(token.expression, self.local_objs)
            if not obj:
                obj = new_lvar(token.expression, self.local_objs[-1])
                self.local_objs.append(obj)
            return new_var_node(obj, token)
        print(error_message(token.expression, token.location, "expected an expression"))
        exit(1)

    def new_add(self, left: Node, right: Node, token: Token) -> Node:
        add_type(left)
        add_type(right)
        if is_integer(left.node_type) and is_integer(right.node_type):
            return new_binary(NodeKind.Add, left, right, token)
        if left.node_type.base and right.node_type.base:
            raise ValueError("pointer + pointer")
        if not left.node_type.base and not right.node_type.base:
            left, right = right, left
        right = new_binary(
            NodeKind.Mul, right, new_number(8, token), self.tokens.peek()
        )
        return new_binary(NodeKind.Add, left, right, token)

    def new_sub(self, left: Node, right: Node, token: Token) -> Node:
        add_type(left)
        add_type(right)
        if is_integer(left.node_type) and is_integer(right.node_type):
            return new_binary(NodeKind.Sub, left, right, token)
        if left.node_type.base and is_integer(right.node_type):
            right = new_binary(
                NodeKind.Mul,
                right,
                new_number(8, self.tokens.peek()),
                self.tokens.peek(),
            )
            add_type(right)
            node = new_binary(NodeKind.Sub, left, right, token)
            node.node_type = left.node_type
            return node
        if left.node_type.base and right.node_type.base:
            node = new_binary(NodeKind.Sub, left, right, token)
            node.node_type = TYPE_INT
            return new_binary(
                NodeKind.Div,
                node,
                new_number(8, self.tokens.peek()),
                self.tokens.peek(),
            )
        raise ValueError("pointer - pointer")


def search_obj(obj: str, local_objs: list["Obj"]) -> Optional[Obj]:
    for local_obj in local_objs:
        if local_obj and local_obj.name == obj:
            return local_obj
    return None
