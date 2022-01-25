
__all__ = ["EXTERN_METHODS", "EXT_EQUALS", "EXT_REPR", "get_ext_eq", "get_ext_repr"]

from functools import lru_cache
from typing import Callable, Dict, Type, TypeVar


# todo: Explain why we have this mechanism using the example of AST.__eq__ not
#  being suitably defined and the fact that monkey patching builtin types is
#  not possible.


T = TypeVar('T')


EXT_EQUALS: str = '__ext_eq__'
EXT_REPR: str = '__ext_repr__'


EXTERN_METHODS: Dict[type, Dict[str, Callable]] = {}


def _extension_type(_cls: type) -> Dict[str, Callable]:
    if _cls in EXTERN_METHODS:
        return EXTERN_METHODS[_cls]
    for typ in EXTERN_METHODS:
        if issubclass(_cls, typ):
            return EXTERN_METHODS[typ]
    return {}


def _get_ext_method(_cls: Type[T], method: str, default: Callable) -> Callable:
    func: Callable = getattr(_cls, method, None)
    if func is not None:
        return func
    func = _extension_type(_cls).get(method)
    return default if func is None else func


@lru_cache(maxsize=None)
def get_ext_eq(_cls: Type[T]) -> Callable[[T, T], bool]:
    return _get_ext_method(_cls, EXT_EQUALS, _cls.__eq__)


@lru_cache(maxsize=None)
def get_ext_repr(_cls: Type[T]) -> Callable[[T], str]:
    return _get_ext_method(_cls, EXT_REPR, _cls.__repr__)
