from dataclasses import dataclass, field
from enum import IntEnum
from typing import Optional


class TypeKind(IntEnum):
    TYPE_INT = 1
    TYPE_PTR = 2
    TYPE_FUNCTION = 3
    TYPE_ARRAY = 4
    TYPE_CHAR = 5


@dataclass
class Type:
    kind: TypeKind = None
    base: Optional["Type"] = None
    name: Optional[str] = None
    return_type: Optional["Type"] = None
    params: list[Optional["Type"]] = field(default_factory=list)
    next_type: Optional["Type"] = None
    size: int = 0
    array_len: int = 0


TYPE_INT = Type(TypeKind.TYPE_INT, size=8)
TYPE_CHAR = Type(TypeKind.TYPE_CHAR, size=1)


def is_integer(ty: Type) -> bool:
    return ty.kind == TypeKind.TYPE_CHAR or ty.kind == TypeKind.TYPE_INT


def pointer_to(base: Type) -> Type:
    return Type(TypeKind.TYPE_PTR, base, size=8)


def function_type(return_type: Type) -> Type:
    return Type(TypeKind.TYPE_FUNCTION, return_type)


def array_of(base: Type, length: int) -> Type:
    return Type(TypeKind.TYPE_ARRAY, base, size=base.size * length, array_len=length)


def copy_type(ty: Type) -> Type:
    return Type(
        ty.kind,
        ty.base,
        ty.name,
        ty.return_type,
        ty.params,
        ty.next_type,
        ty.size,
        ty.array_len,
    )
