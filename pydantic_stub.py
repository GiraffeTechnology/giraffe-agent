"""Thin re-export shim so ``import pydantic_stub`` resolves without error.

When pydantic is installed (the normal case for this project) this module
simply forwards the real symbols.  The fallback minimal implementation lets
the integration package run in stripped environments where pydantic is absent.
"""

try:
    from pydantic import BaseModel, Field
    from pydantic import field_validator as validator
    from pydantic import model_validator

    __all__ = ["BaseModel", "Field", "validator", "model_validator"]

except ImportError:  # pragma: no cover — only reached without pydantic

    class Field:  # type: ignore[no-redef]
        def __init__(self, default=None, **kw):
            self.default = default

    class _ModelMeta(type):
        def __new__(mcs, name, bases, ns):
            cls = super().__new__(mcs, name, bases, ns)
            annotations: dict = {}
            for b in reversed(bases):
                annotations.update(getattr(b, "__annotations__", {}))
            annotations.update(ns.get("__annotations__", {}))
            cls.__annotations__ = annotations
            return cls

    class BaseModel(metaclass=_ModelMeta):  # type: ignore[no-redef]
        def __init__(self, **data):
            for k, v in data.items():
                setattr(self, k, v)

        def model_dump(self) -> dict:
            return {k: getattr(self, k, None) for k in self.__annotations__}

    def validator(*fields, **kw):  # type: ignore[misc]
        def decorator(fn):
            return fn
        return decorator

    def model_validator(**kw):  # type: ignore[misc]
        def decorator(fn):
            return fn
        return decorator

    __all__ = ["BaseModel", "Field", "validator", "model_validator"]
