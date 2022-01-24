
__all__ = ["EXTENSIONS", "EXT_EQUALS", "EXT_REPR", "get_ext_method"]

from functools import lru_cache
from typing import Callable, Dict, Type, TypeVar


T = TypeVar('T')


EXT_EQUALS = 'te_equals'
EXT_REPR = 'te_repr'


EXTENSIONS: Dict[type, Dict[str, Callable]] = {}


def _extension_type(_cls: type) -> Dict[str, Callable]:
    if _cls in EXTENSIONS:
        return EXTENSIONS[_cls]
    for typ in EXTENSIONS:
        if issubclass(_cls, typ):
            return EXTENSIONS[typ]
    return {}


@lru_cache(maxsize=None)
def get_ext_method(_cls: Type[T], method: str, default: Callable) -> Callable:
    func: Callable = getattr(_cls, method, None)
    if func is not None:
        return func
    func = _extension_type(_cls).get(method)
    return default if func is None else func
