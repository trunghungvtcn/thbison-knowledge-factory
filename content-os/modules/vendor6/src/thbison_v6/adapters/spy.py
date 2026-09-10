from __future__ import annotations

from typing import Any, Callable


class SpyAdapter:
    """Records every attribute call. Delegates to inner. Not a verified component."""

    verified_component = False
    transport_name = "spy"

    def __init__(self, inner: Any, name: str = "spy"):
        object.__setattr__(self, "_inner", inner)
        object.__setattr__(self, "_name", name)
        object.__setattr__(self, "calls", [])
        object.__setattr__(self, "kind", getattr(inner, "kind", "ACTUAL"))
        object.__setattr__(self, "vendor", getattr(inner, "vendor", "probe"))

    def __getattr__(self, name: str) -> Callable:
        inner = object.__getattribute__(self, "_inner")
        attr = getattr(inner, name)

        def wrapper(*args: Any, **kwargs: Any) -> Any:
            self.calls.append({"method": name, "args": args, "kwargs": kwargs})
            return attr(*args, **kwargs)

        return wrapper
