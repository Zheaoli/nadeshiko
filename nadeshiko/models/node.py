from dataclasses import dataclass
from enum import IntEnum
from lib2to3.pytree import Node
from typing import Optional


class NodeType(IntEnum):
    Add = 1
    Sub = 2
    Mul = 3
    Div = 4
    Number = 5


@dataclass
class Node:
    kind: Optional[NodeType]
    left: Optional["Node"]
    right: Optional["Node"]
    value: Optional[int]


def new_node(kind: NodeType) -> Node:
    return Node(kind, None, None, None)


def new_binary(kind: NodeType, left: Node, right: Node) -> Node:
    node = new_node(kind)
    node.left = left
    node.right = right
    return node


def new_number(value: int) -> Node:
    return Node(NodeType.Number, None, None, value)
