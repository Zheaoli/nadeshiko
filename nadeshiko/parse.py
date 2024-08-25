from typing import Optional

from nadeshiko.helper import error_message
from nadeshiko.node import (
    Node,
    new_binary,
    NodeType,
    new_unary,
    new_number,
    new_var_node,
    Obj,
    new_lvar,
    Function,
    new_node,
)
from nadeshiko.token import TokenType, equal, skip, Token
from nadeshiko.utils import Peekable


class Parse:
    tokens: Peekable[Optional[Token]]

    def __init__(self, tokens: Peekable[Optional[Token]]) -> None:
        self.tokens = tokens

    def parse_stmt(self) -> Optional["Function"]:
        skip(next(self.tokens), "{")
        local_objs: list[Optional["Obj"]] = [None]
        node = self.convert_compound_stmt(local_objs)
        local_objs.pop(0)
        return Function(node, local_objs, 0)

    def parse_stmt_return(self, local_objs: list[Optional["Obj"]]) -> Optional[Node]:
        token = self.tokens.peek()
        if equal(token, "return"):
            next(self.tokens)
            node = self.expression_parse(local_objs)
            node = new_unary(NodeType.Return, node, token)
            skip(next(self.tokens), ";")
            return node
        if equal(token, "if"):
            node = new_node(NodeType.If, token)
            next(self.tokens)
            skip(next(self.tokens), "(")
            node.condition = self.expression_parse(local_objs)
            skip(next(self.tokens), ")")
            node.then = self.parse_stmt_return(local_objs)
            if equal(self.tokens.peek(), "else"):
                next(self.tokens)
                node.els = self.parse_stmt_return(local_objs)
            return node
        if equal(token, "while"):
            node = new_node(NodeType.ForStmt, token)
            next(self.tokens)
            skip(next(self.tokens), "(")
            node.condition = self.expression_parse(local_objs)
            skip(next(self.tokens), ")")
            node.then = self.parse_stmt_return(local_objs)
            return node
        if equal(token, "for"):
            node = new_node(NodeType.ForStmt, token)
            next(self.tokens)
            skip(next(self.tokens), "(")
            node.init = self.expression_parse_stmt(local_objs)
            if not equal(self.tokens.peek(), ";"):
                node.condition = self.expression_parse(local_objs)
            skip(next(self.tokens), ";")
            if not equal(self.tokens.peek(), ")"):
                node.inc = self.expression_parse(local_objs)
            skip(next(self.tokens), ")")
            node.then = self.parse_stmt_return(local_objs)
            return node

        if equal(token, "{"):
            next(self.tokens)
            return self.convert_compound_stmt(local_objs)
        return self.expression_parse_stmt(local_objs)

    def expression_parse_stmt(
        self, local_objs: list[Optional["Obj"]]
    ) -> Optional[Node]:
        token = self.tokens.peek()
        if equal(token, ";"):
            next(self.tokens)
            return new_node(NodeType.Block, token)
        node = self.expression_parse(local_objs)
        node = new_unary(NodeType.ExpressionStmt, node, token)
        skip(next(self.tokens), ";")
        return node

    def expression_parse(self, local_objs: list[Optional["Obj"]]) -> Optional[Node]:
        return self.convert_assign_token(local_objs)

    def convert_compound_stmt(
        self, local_objs: list[Optional["Obj"]]
    ) -> Optional[Node]:
        head = new_node(NodeType.Block, self.tokens.peek())
        current = head
        while not equal(self.tokens.peek(), "}"):
            node = self.parse_stmt_return(local_objs)
            current.next_node = node
            current = node
        node = new_node(NodeType.Block, self.tokens.peek())
        node.body = head.next_node
        next(self.tokens)
        return node

    def convert_relational_token(
        self, local_objs: list[Optional["Obj"]]
    ) -> Optional[Node]:
        node = self.convert_add_token(local_objs)
        while True:
            token = self.tokens.peek()
            if equal(token, "<") or equal(token, ">"):
                next(self.tokens)
                next_node = self.convert_add_token(local_objs)
                left_node = node if equal(token, "<") else next_node
                right_node = next_node if equal(token, "<") else node
                node = new_binary(NodeType.Less, left_node, right_node, token)
                continue
            if equal(token, "<=") or equal(token, ">="):
                next(self.tokens)
                next_node = self.convert_add_token(local_objs)
                left_node = node if equal(token, "<=") else next_node
                right_node = next_node if equal(token, "<=") else node
                node = new_binary(NodeType.LessEqual, left_node, right_node, token)
                continue
            return node

    def convert_assign_token(self, local_objs: list[Optional["Obj"]]) -> Optional[Node]:
        node = self.convert_equality_token(local_objs)
        if equal(self.tokens.peek(), "="):
            token = next(self.tokens)
            next_node = self.convert_assign_token(local_objs)
            node = new_binary(NodeType.Assign, node, next_node, token)
        return node

    def convert_equality_token(
        self, local_objs: list[Optional["Obj"]]
    ) -> Optional[Node]:
        node = self.convert_relational_token(local_objs)
        while True:
            token = self.tokens.peek()
            if equal(token, "=="):
                next(self.tokens)
                next_node = self.convert_relational_token(local_objs)
                node = new_binary(NodeType.Equal, node, next_node, token)
                continue
            if equal(token, "!="):
                next(self.tokens)
                next_node = self.convert_relational_token(local_objs)
                node = new_binary(NodeType.NotEqual, node, next_node, token)
                continue
            return node

    def convert_add_token(self, local_objs: list[Optional["Obj"]]) -> Optional[Node]:
        node = self.convert_mul_token(local_objs)
        while True:
            token = self.tokens.peek()
            if equal(token, "+"):
                next(self.tokens)
                next_node = self.convert_mul_token(local_objs)
                node = new_binary(NodeType.Add, node, next_node, token)
                continue
            if equal(token, "-"):
                next(self.tokens)
                next_node = self.convert_mul_token(local_objs)
                node = new_binary(NodeType.Sub, node, next_node, token)
                continue
            return node

    def convert_unary_token(self, local_objs: list[Optional["Obj"]]) -> Optional[Node]:
        token = self.tokens.peek()
        if equal(token, "+"):
            next(self.tokens)
            return self.convert_unary_token(local_objs)
        if equal(token, "-"):
            next(self.tokens)
            node = self.convert_unary_token(local_objs)
            node = new_unary(NodeType.Neg, node, token)
            return node
        if equal(token, "&"):
            next(self.tokens)
            node = self.primary_token(local_objs)
            node = new_unary(NodeType.Addr, node, token)
            return node
        if equal(token, "*"):
            next(self.tokens)
            node = self.convert_unary_token(local_objs)
            node = new_unary(NodeType.Deref, node, token)
            return node
        return self.primary_token(local_objs)

    def convert_mul_token(self, local_objs: list[Optional["Obj"]]) -> Optional[Node]:
        node = self.convert_unary_token(local_objs)
        while True:
            token = self.tokens.peek()
            if equal(token, "*"):
                next(self.tokens)
                next_node = self.primary_token(local_objs)
                node = new_binary(NodeType.Mul, node, next_node, token)
                continue
            if equal(token, "/"):
                next(self.tokens)
                next_node = self.primary_token(local_objs)
                node = new_binary(NodeType.Div, node, next_node, token)
                continue
            return node

    def primary_token(self, local_objs: list[Optional["Obj"]]) -> Optional[Node]:
        token = self.tokens.peek()
        if equal(token, "("):
            next(self.tokens)
            next_node = self.expression_parse(local_objs)
            skip(next(self.tokens), ")")
            return next_node
        if token.type == TokenType.Number:
            next(self.tokens)
            return new_number(token.value, token)
        if token.type == TokenType.Identifier:
            next(self.tokens)
            obj = search_obj(token.expression, local_objs)
            if not obj:
                obj = new_lvar(token.expression, local_objs[-1])
                local_objs.append(obj)
            return new_var_node(obj, token)
        print(error_message(token.expression, token.location, "expected an expression"))
        exit(1)


def search_obj(obj: str, local_objs: list[Optional["Obj"]]) -> Optional[Obj]:
    for local_obj in local_objs:
        if local_obj and local_obj.name == obj:
            return local_obj
    return None
