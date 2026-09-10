from __future__ import annotations

import importlib
import sys
import threading
from collections.abc import Mapping, MutableMapping
from functools import update_wrapper
from types import ModuleType
from typing import Any, Callable

_MODULES: dict[str, ModuleType] = {}
_RESOLVED_EXPORTS: dict[str, set[str]] = {}
_LOCK = threading.RLock()


def _load_module(module_name: str) -> ModuleType:
    module = _MODULES.get(module_name)
    if module is not None:
        return module
    with _LOCK:
        module = _MODULES.get(module_name)
        if module is None:
            module = importlib.import_module(module_name)
            _MODULES[module_name] = module
            _RESOLVED_EXPORTS.setdefault(module_name, set())
        return module


def resolve_lazy_attribute(module_name: str, attribute_name: str) -> Any:
    module = _load_module(module_name)
    value = getattr(module, attribute_name)
    with _LOCK:
        _RESOLVED_EXPORTS.setdefault(module_name, set()).add(attribute_name)
    return value


def lazy_callable(module_name: str, attribute_name: str, *, public_name: str | None = None) -> Callable[..., Any]:
    resolved: Callable[..., Any] | None = None
    resolution_lock = threading.Lock()

    def call(*args: Any, **kwargs: Any) -> Any:
        nonlocal resolved
        target = resolved
        if target is None:
            with resolution_lock:
                target = resolved
                if target is None:
                    loaded = resolve_lazy_attribute(module_name, attribute_name)
                    if not callable(loaded):
                        raise TypeError(f"Lazy dashboard export {module_name}.{attribute_name} is not callable.")
                    resolved = loaded
                    target = loaded
                    try:
                        update_wrapper(call, loaded)
                    except (AttributeError, TypeError):
                        pass
        return target(*args, **kwargs)

    call.__name__ = public_name or attribute_name
    call.__qualname__ = public_name or attribute_name
    call.__module__ = "dashboard"
    call.__doc__ = f"Lazily resolves {module_name}.{attribute_name} on first use."
    setattr(call, "__eidolon_lazy_module__", module_name)
    setattr(call, "__eidolon_lazy_attribute__", attribute_name)
    return call


def install_lazy_callables(
    namespace: MutableMapping[str, Any],
    module_name: str,
    exports: Mapping[str, str] | list[str] | tuple[str, ...],
) -> tuple[str, ...]:
    mapping = {name: name for name in exports} if not isinstance(exports, Mapping) else dict(exports)
    installed: list[str] = []
    for public_name, attribute_name in mapping.items():
        if not public_name or not attribute_name:
            raise ValueError("Lazy dashboard exports require non-empty names.")
        namespace[public_name] = lazy_callable(module_name, attribute_name, public_name=public_name)
        installed.append(public_name)
    return tuple(installed)


def lazy_import_status(module_names: list[str] | tuple[str, ...] | None = None) -> dict[str, dict[str, Any]]:
    names = sorted(set(module_names or tuple(_RESOLVED_EXPORTS) + tuple(_MODULES)))
    return {
        name: {
            "loaded": name in _MODULES or name in sys.modules,
            "resolved_export_count": len(_RESOLVED_EXPORTS.get(name, set())),
            "resolved_exports": sorted(_RESOLVED_EXPORTS.get(name, set())),
        }
        for name in names
    }
