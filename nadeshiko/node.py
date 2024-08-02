from dataclasses import dataclass
from enum import IntEnum
from typing import Optional


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


@dataclass
class Node:
    kind: Optional[NodeType]
    next_node: Optional["Node"]
    left: Optional["Node"]
    right: Optional["Node"]
    value: Optional[int]
    name: Optional[str]


def new_node(kind: NodeType) -> Node:
    return Node(kind, None, None, None, None, None)


def new_binary(kind: NodeType, left: Node, right: Node) -> Node:
    node = new_node(kind)
    node.left = left
    node.right = right
    return node


def new_number(value: int) -> Node:
    return Node(NodeType.Number, None, None, None, value, None)


def new_unary(node_type: NodeType, node: Node) -> Node:
    return Node(node_type, None, node, None, None, None)


def new_var_node(name: str) -> Node:
    return Node(NodeType.Variable, None, None, None, None, name)
