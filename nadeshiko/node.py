from dataclasses import dataclass
from enum import IntEnum
from typing import Optional

from nadeshiko.token import Token


class NodeType(IntEnum):
    Add = 1
    Sub = 2
    Mul = 3
    Div = 4
    Neg = 5
    Number = 6
    Equal = 7
    NotEqual = 8
    Less = 9
    LessEqual = 10
    ExpressionStmt = 11
    Assign = 12
    Variable = 13
    Return = 14
    Block = 15
    If = 16
    ForStmt = 17


@dataclass
class Node:
    kind: Optional[NodeType] = None
    next_node: Optional["Node"] = None
    left: Optional["Node"] = None
    right: Optional["Node"] = None
    value: Optional[int] = None
    var: Optional["Obj"] = None
    body: Optional["Node"] = None
    condition: Optional["Node"] = None
    then: Optional["Node"] = None
    els: Optional["Node"] = None
    init: Optional["Node"] = None
    inc: Optional["Node"] = None
    token: Optional["Token"] = None


@dataclass
class Obj:
    next_obj: Optional["Obj"]
    name: Optional[str]
    offset: Optional[int]


@dataclass
class Function:
    body: Optional[Node]
    locals_obj: list[Optional["Obj"]]
    stack_size: Optional[int]


def new_node(kind: NodeType, token: Token) -> Node:
    node = Node(kind)
    node.token = token
    return node


def new_binary(kind: NodeType, left: Node, right: Node, token: Token) -> Node:
    node = new_node(kind, token)
    node.left = left
    node.right = right
    return node


def new_number(value: int, token: Token) -> Node:
    node = new_node(NodeType.Number, token)
    node.value = value
    return node


def new_unary(node_type: NodeType, left_node: Node, token: Token) -> Node:
    node = new_node(node_type, token)
    node.left = left_node
    return node


def new_var_node(obj: Obj, token: Token) -> Node:
    node = new_node(NodeType.Variable, token)
    node.var = obj
    return node


def new_lvar(name: str, next_obj: Obj) -> Obj:
    return Obj(next_obj, name, 0)
