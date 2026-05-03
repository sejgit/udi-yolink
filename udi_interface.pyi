import logging
from typing import Any


LOGGER: logging.Logger


class Custom(dict[str, Any]):
    def __init__(self, *args: Any, **kwargs: Any) -> None: ...


class Node:
    def __init__(self, *args: Any, **kwargs: Any) -> None: ...