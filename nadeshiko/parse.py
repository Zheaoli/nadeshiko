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
from nadeshiko.tokenize import consume
from nadeshiko.type import (
    is_integer,
    TYPE_INT,
    pointer_to,
    Type,
    function_type,
    copy_type,
    array_of,
)
from nadeshiko.utils import Peekable


class Parse:
    tokens: Peekable[Optional[Token]]
    local_objs: list[Optional["Obj"]]

    def __init__(self, tokens: Peekable[Optional[Token]]) -> None:
        self.tokens = tokens
        self.local_objs = [None]

    def function(self) -> Optional["Function"]:
        obj_type = self.declspac()
        obj_type = self.declarator(obj_type)
        function = Function(None, [], None)
        self.local_objs = [None]
        self.create_param_lvars(obj_type)
        self.local_objs.pop(0)
        function.params = self.local_objs.copy()[: len(self.local_objs) - 1]

        skip(next(self.tokens), "{")
        node = self.convert_compound_stmt()
        function.body = node
        function.stack_size = 0
        function.locals_obj = self.local_objs.copy()
        function.name = obj_type.name
        return function

    def parse_stmt(self) -> list["Function"]:
        functions = []
        while self.tokens.peek().type != TokenType.EOF:
            functions.append(self.function())
        return functions

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
            if equal(self.tokens.peek(), "int"):
                node = self.declaration()
            else:
                node = self.parse_stmt_return()
            add_type(node)
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
            last_token = next(self.tokens)
            if equal(self.tokens.peek(), "("):
                return self.function_call(last_token)
            obj = search_obj(token.expression, self.local_objs)
            if not obj:
                print(
                    error_message(
                        token.expression, token.location, "undefined variable"
                    )
                )
                exit(1)
            return new_var_node(obj, token)
        print(error_message(token.expression, token.location, "expected an expression"))
        exit(1)

    def function_call(self, function_token: Token) -> Optional["Node"]:
        token = function_token
        skip(next(self.tokens), "(")
        nodes = []
        while not equal(self.tokens.peek(), ")"):
            if nodes:
                skip(next(self.tokens), ",")
            nodes.append(self.convert_assign_token())
        skip(next(self.tokens), ")")
        node = new_node(NodeKind.FunctionCall, token)
        node.function_name = token.expression
        node.function_args = nodes
        return node

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
            NodeKind.Mul,
            right,
            new_number(left.node_type.base.size, token),
            self.tokens.peek(),
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
                new_number(left.node_type.base.size, self.tokens.peek()),
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
                new_number(left.node_type.base.size, self.tokens.peek()),
                self.tokens.peek(),
            )
        raise ValueError("pointer - pointer")

    def get_indet(self, token: Token) -> str:
        if token.type != TokenType.Identifier:
            print(
                error_message(
                    token.original_expression, token.location, "expected identifier"
                )
            )
            exit(1)
        return token.expression

    def declspac(self) -> Optional["Type"]:
        token = self.tokens.peek()
        if equal(token, "int"):
            next(self.tokens)
            return TYPE_INT
        print(error_message(token.expression, token.location, "expected type"))
        exit(1)

    def declarator(self, obj_type: Optional["Type"]) -> Optional["Type"]:
        while consume(self.tokens, "*"):
            obj_type = pointer_to(obj_type)
        if self.tokens.peek().type != TokenType.Identifier:
            print(
                error_message(
                    self.tokens.peek().original_expression,
                    self.tokens.peek().location,
                    "expected identifier",
                )
            )
            exit(1)
        last_token = next(self.tokens)
        obj_type = self.type_suffix(obj_type)
        obj_type.name = last_token.expression
        return obj_type

    def declaration(self) -> Optional["Node"]:
        base_type = self.declspac()
        head = Node(NodeKind.Block)
        current = head
        i = 0
        while not equal(self.tokens.peek(), ";"):
            i += 1
            if i > 1:
                skip(next(self.tokens), ",")
            obj_type = self.declarator(base_type)
            obj = new_lvar(
                obj_type.name, self.local_objs[-1], obj_type, self.local_objs
            )
            if not equal(self.tokens.peek(), "="):
                continue
            left_node = new_var_node(obj, self.tokens.peek())
            next(self.tokens)
            right_node = self.convert_assign_token()
            node = new_binary(
                NodeKind.Assign, left_node, right_node, self.tokens.peek()
            )
            current.next_node = new_unary(
                NodeKind.ExpressionStmt, node, self.tokens.peek()
            )
            current = current.next_node

        node = new_node(NodeKind.Block, self.tokens.peek())
        node.body = head.next_node
        next(self.tokens)
        return node

    def func_params(self, node_type: Optional["Type"]) -> Type:
        type_objs = []
        while not equal(self.tokens.peek(), ")"):
            if type_objs:
                skip(next(self.tokens), ",")
            base_type = self.declspac()
            obj_type = self.declarator(base_type)
            type_objs.append(copy_type(obj_type))
        func_type = function_type(node_type)
        func_type.params = type_objs
        skip(next(self.tokens), ")")
        return func_type

    def type_suffix(self, node_type: Optional["Type"]) -> Type:
        if equal(self.tokens.peek(), "("):
            next(self.tokens)
            return self.func_params(node_type)
        if equal(self.tokens.peek(), "["):
            next(self.tokens)
            size = get_number(next(self.tokens))
            skip(next(self.tokens), "]")
            node_type = self.type_suffix(node_type)
            return array_of(node_type, size)
        return node_type

    def create_param_lvars(self, param: Optional["Type"]) -> None:
        if not param:
            return
        for temp_param in param.params:
            self.create_param_lvars(temp_param)
        new_lvar(param.name, self.local_objs[-1], param, self.local_objs)


def search_obj(obj: str, local_objs: list["Obj"]) -> Optional[Obj]:
    for local_obj in local_objs:
        if local_obj and local_obj.name == obj:
            return local_obj
    return None


def get_number(token: Token) -> int:
    if token.type != TokenType.Number:
        print(
            error_message(token.original_expression, token.location, "expected number")
        )
        exit(1)
    return token.value
