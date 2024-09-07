from dataclasses import dataclass, field
from enum import IntEnum
from typing import Optional

from nadeshiko.token import Token
from nadeshiko.type import pointer_to, TYPE_INT, Type, TypeKind


class NodeKind(IntEnum):
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
    Addr = 18
    Deref = 19
    FunctionCall = 20


@dataclass
class Node:
    kind: Optional[NodeKind] = None
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
    node_type: Optional["Type"] = None
    function_name: Optional[str] = None
    function_args: list[Optional["Node"]] = None


@dataclass
class Obj:
    next_obj: Optional["Obj"] = None
    name: Optional[str] = None
    offset: Optional[int] = None
    object_type: Optional["Type"] = None


@dataclass
class Function:
    body: Optional[Node]
    locals_obj: list[Optional["Obj"]]
    stack_size: Optional[int]
    next_function: Optional["Function"] = field(default_factory=list)
    name: Optional[str] = None


def new_node(kind: NodeKind, token: Token) -> Node:
    node = Node(kind)
    node.token = token
    return node


def new_binary(kind: NodeKind, left: Node, right: Node, token: Token) -> Node:
    node = new_node(kind, token)
    node.left = left
    node.right = right
    return node


def new_number(value: int, token: Token) -> Node:
    node = new_node(NodeKind.Number, token)
    node.value = value
    return node


def new_unary(node_type: NodeKind, left_node: Node, token: Token) -> Node:
    node = new_node(node_type, token)
    node.left = left_node
    return node


def new_var_node(obj: Obj, token: Token) -> Node:
    node = new_node(NodeKind.Variable, token)
    node.var = obj
    return node


def new_lvar(
    name: str, next_obj: Obj, object_type: Optional["Type"], objs: list["Obj"]
) -> Obj:
    obj = Obj(next_obj, name, 0, object_type)
    objs.append(obj)
    return obj


def add_type(node: Node) -> None:
    if not node or node.node_type:
        return
    add_type(node.left)
    add_type(node.right)
    add_type(node.condition)
    add_type(node.then)
    add_type(node.els)
    add_type(node.init)
    add_type(node.inc)
    current = node.body
    while current:
        add_type(current)
        current = current.next_node
    match node.kind:
        case (
            NodeKind.Add
            | NodeKind.Sub
            | NodeKind.Mul
            | NodeKind.Div
            | NodeKind.Neg
            | NodeKind.Assign
        ):
            node.node_type = node.left.node_type
            return
        case (
            NodeKind.Equal
            | NodeKind.NotEqual
            | NodeKind.Less
            | NodeKind.LessEqual
            | NodeKind.Number
            | NodeKind.FunctionCall
        ):
            node.node_type = TYPE_INT
            return
        case NodeKind.Variable:
            node.node_type = node.var.object_type
            return
        case NodeKind.Addr:
            node.node_type = pointer_to(node.left.node_type)
            return
        case NodeKind.Deref:
            if node.left.node_type.kind == TypeKind.TYPE_PTR:
                raise ValueError("invalid pointer dereference")
            node.node_type = node.left.node_type.base
            return
