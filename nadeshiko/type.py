from dataclasses import dataclass, field
from enum import IntEnum
from typing import Optional


class TypeKind(IntEnum):
    TYPE_INT = 1
    TYPE_PTR = 2
    TYPE_FUNCTION = 3


@dataclass
class Type:
    kind: TypeKind = None
    base: Optional["Type"] = None
    name: Optional[str] = None
    return_type: Optional["Type"] = None
    params: list[Optional["Type"]] = field(default_factory=list)
    next_type: Optional["Type"] = None


TYPE_INT = Type(TypeKind.TYPE_INT)


def is_integer(ty: Type) -> bool:
    return ty.kind == TypeKind.TYPE_INT


def pointer_to(base: Type) -> Type:
    return Type(TypeKind.TYPE_PTR, base)


def function_type(return_type: Type) -> Type:
    return Type(TypeKind.TYPE_FUNCTION, return_type)


def copy_type(ty: Type) -> Type:
    return Type(ty.kind, ty.base, ty.name, ty.return_type, ty.params, ty.next_type)
