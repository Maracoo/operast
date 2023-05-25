__all__ = [
    "EXTERN_METHODS",
    "EXT_EQUALS",
    "EXT_REPR",
    "ExternMethods",
    "get_ext_eq",
    "get_ext_repr",
]

from collections.abc import Callable
from dataclasses import dataclass
from functools import cache
from typing import Final, Generic, LiteralString, TypeVar

# todo: Explain why we have this mechanism using the example of AST.__eq__ not
#  being suitably defined and the fact that monkey patching builtin types is
#  not possible.


T = TypeVar("T")


EXT_EQUALS: Final[LiteralString] = "__ext_eq__"
EXT_REPR: Final[LiteralString] = "__ext_repr__"


@dataclass
class ExternMethods(Generic[T]):
    eq: Callable[[T, object], bool]
    repr: Callable[[T], str]


EXTERN_METHODS: dict[type, ExternMethods] = {}


def _extension_type(_cls: type) -> ExternMethods | None:
    if _cls in EXTERN_METHODS:
        return EXTERN_METHODS[_cls]
    for typ in EXTERN_METHODS:
        if issubclass(_cls, typ):
            return EXTERN_METHODS[typ]
    return None


@cache
def get_ext_eq(_cls: type[T]) -> Callable[[T, object], bool]:
    eq: Callable[[T, object], bool] | None = getattr(_cls, EXT_EQUALS, None)
    if eq is None and (extensions := _extension_type(_cls)) is not None:
        eq = extensions.eq
    return _cls.__eq__ if eq is None else eq


@cache
def get_ext_repr(_cls: type[T]) -> Callable[[T], str]:
    _repr: Callable[[T], str] | None = getattr(_cls, EXT_EQUALS, None)
    if _repr is None and (extensions := _extension_type(_cls)) is not None:
        _repr = extensions.repr
    return _cls.__repr__ if _repr is None else _repr
