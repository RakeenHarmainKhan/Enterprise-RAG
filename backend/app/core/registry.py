"""Generic plugin registry: register(name) decorator and resolve(name)."""

from collections.abc import Callable
from typing import Any, Generic, TypeVar

T = TypeVar("T")


class PluginRegistry(Generic[T]):
    """Maps string plugin names to factory callables or types."""

    def __init__(self) -> None:
        self._entries: dict[str, Callable[..., T] | type[T]] = {}

    def register(self, name: str) -> Callable[[Callable[..., T] | type[T]], Callable[..., T] | type[T]]:
        """Decorator to register a plugin under ``name``."""

        def decorator(
            obj: Callable[..., T] | type[T],
        ) -> Callable[..., T] | type[T]:
            self._entries[name] = obj
            return obj

        return decorator

    def resolve(self, name: str) -> Callable[..., T] | type[T]:
        """Return the registered factory or class for ``name``."""
        if name not in self._entries:
            msg = f"Unknown plugin: {name!r}. Registered: {sorted(self._entries)}"
            raise KeyError(msg)
        return self._entries[name]

    def build(self, name: str, *args: Any, **kwargs: Any) -> T:
        """Instantiate plugin ``name`` with constructor args."""
        target = self.resolve(name)
        if isinstance(target, type):
            return target(*args, **kwargs)
        return target(*args, **kwargs)

    def names(self) -> list[str]:
        """All registered plugin names."""
        return sorted(self._entries)
