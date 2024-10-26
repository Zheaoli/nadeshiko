import copy
from typing import Optional

from nadeshiko.context import CURRENT_VAR_ID
from nadeshiko.helper import error_message
from nadeshiko.node import (
    Node,
    new_binary,
    NodeKind,
    new_unary,
    new_number,
    new_var_node,
    Obj,
    new_local_var,
    new_node,
    add_type,
    new_global_var,
    Scope,
    enter_scope,
    leave_scope,
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
    TypeKind,
    TYPE_CHAR,
)
from nadeshiko.utils import Peekable


class Parse:
    tokens: Peekable[Optional[Token]]
    local_objs: list[Optional["Obj"]]
    scope: Optional["Scope"] = None

    def __init__(self, tokens: Peekable[Optional[Token]]) -> None:
        self.tokens = tokens
        self.local_objs = [None]
        self.global_objs: list[Obj] = []
        self.scope = Scope()

    def function(self, basic_type: Type) -> Optional["Obj"]:
        obj_type = self.declarator(basic_type)
        function = new_global_var(obj_type.name, obj_type, self.global_objs, self.scope)
        function.is_function = True
        self.local_objs = [None]
        self.scope = enter_scope(self.scope)
        self.create_param_local_vars(obj_type.params)
        self.local_objs.pop(0)
        function.params = self.local_objs.copy()
        skip(next(self.tokens), "{")
        node = self.convert_compound_stmt()
        function.body = node
        function.stack_size = 0
        function.locals_obj = self.local_objs.copy()
        function.name = obj_type.name
        self.scope = leave_scope(self.scope)
        return function

    def is_function(self) -> bool:
        if equal(self.tokens.peek(), ";"):
            return False
        tokens = copy.deepcopy(self.tokens)
        dummy_type = Type()
        obj_type = self.declarator(dummy_type)
        self.tokens = tokens
        return obj_type.kind == TypeKind.TYPE_FUNCTION

    def global_variable(self, basic_type: Type) -> list["Obj"]:
        first = True
        results = []
        while not equal(self.tokens.peek(), ";"):
            if not first:
                skip(next(self.tokens), ",")
            first = False
            obj_type = self.declarator(basic_type)
            new_global_var(obj_type.name, obj_type, results, self.scope)
        next(self.tokens)
        self.global_objs.extend(results)
        return results

    def parse_stmt(self) -> list["Obj"]:
        objs = []
        while self.tokens.peek().kind != TokenType.EOF:
            basic_type = self.declaration_spec()
            if self.is_function():
                objs.append(self.function(basic_type))
                continue
            self.global_variable(basic_type)
        objs.extend([item for item in self.global_objs if not item.is_function])
        return objs

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
        self.scope = enter_scope(self.scope)
        while not equal(self.tokens.peek(), "}"):
            if is_type_name(self.tokens.peek()):
                node = self.declaration()
            else:
                node = self.parse_stmt_return()
            add_type(node)
            current.next_node = node
            current = node
        self.scope = leave_scope(self.scope)
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
        return self.postfix()

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
            if equal(self.tokens.peek(), "{"):
                next(self.tokens)
                node = new_node(NodeKind.StmtExpression, self.tokens.peek())
                node.body = self.convert_compound_stmt().body
                skip(next(self.tokens), ")")
                return node
            next_node = self.expression_parse()
            skip(next(self.tokens), ")")
            return next_node
        if equal(token, "sizeof"):
            next(self.tokens)
            token = self.tokens.peek()
            node = self.convert_unary_token()
            add_type(node)
            return new_number(node.node_type.size, token)
        if token.kind == TokenType.Number:
            next(self.tokens)
            return new_number(token.value, token)
        if token.kind == TokenType.STRING:
            var = new_string_literal(
                token.str_value, token.str_type, self.global_objs, self.scope
            )
            next(self.tokens)
            return new_var_node(var, token)
        if token.kind == TokenType.Identifier:
            last_token = next(self.tokens)
            if equal(self.tokens.peek(), "("):
                return self.function_call(last_token)
            obj = search_obj(token.expression, self.scope)
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
        if not left.node_type.base and right.node_type.base:
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
        if token.kind != TokenType.Identifier:
            print(
                error_message(
                    token.original_expression, token.location, "expected identifier"
                )
            )
            exit(1)
        return token.expression

    def declaration_spec(self) -> Optional["Type"]:
        token = self.tokens.peek()
        if equal(token, "char"):
            next(self.tokens)
            return TYPE_CHAR
        if equal(token, "int"):
            next(self.tokens)
            return TYPE_INT
        print(error_message(token.expression, token.location, "expected type"))
        exit(1)

    def declarator(self, obj_type: Optional["Type"]) -> Optional["Type"]:
        while consume(self.tokens, "*"):
            obj_type = pointer_to(obj_type)
        if self.tokens.peek().kind != TokenType.Identifier:
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
        base_type = self.declaration_spec()
        head = Node(NodeKind.Block)
        current = head
        i = 0
        while not equal(self.tokens.peek(), ";"):
            i += 1
            if i > 1:
                skip(next(self.tokens), ",")
            obj_type = self.declarator(base_type)
            obj = new_local_var(obj_type.name, obj_type, self.local_objs, self.scope)
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
            base_type = self.declaration_spec()
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

    def create_param_local_vars(self, params: list[Optional["Type"]]) -> None:
        if not params:
            return
        for temp_param in params:
            self.create_param_local_vars(temp_param.params)
            new_local_var(temp_param.name, temp_param, self.local_objs, self.scope)

    def postfix(self) -> Optional["Node"]:
        node = self.primary_token()
        while equal(self.tokens.peek(), "["):
            next(self.tokens)
            token = self.tokens.peek()
            index_node = self.expression_parse()
            skip(next(self.tokens), "]")
            node = new_unary(
                NodeKind.Deref,
                self.new_add(node, index_node, token),
                token,
            )
        return node


def search_obj(obj: str, scope: Optional["Scope"]) -> Optional[Obj]:
    while scope:
        var_scope = scope.vars
        while var_scope:
            if var_scope.name == obj:
                return var_scope.var
            var_scope = var_scope.next_scope
        scope = scope.next_scope
    return None


def get_number(token: Token) -> int:
    if token.kind != TokenType.Number:
        print(
            error_message(token.original_expression, token.location, "expected number")
        )
        exit(1)
    return token.value


def is_type_name(token: Token) -> bool:
    return equal(token, "int") or equal(token, "char")


def net_unique_name() -> str:
    current_id = CURRENT_VAR_ID.get()
    CURRENT_VAR_ID.set(current_id + 1)
    return f".L..{current_id}"


def new_anon_gvar(
    node_type: Type, global_objs: list["Obj"], scope: Optional["Scope"]
) -> Obj:
    name = net_unique_name()
    return new_global_var(name, node_type, global_objs, scope)


def new_string_literal(
    string_value: str,
    node_type: Type,
    global_objs: list["Obj"],
    scope: Optional["Scope"],
) -> Obj:
    var = new_anon_gvar(node_type, global_objs, scope)
    var.init_data = string_value
    return var
