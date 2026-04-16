import logging as _logging
from types import SimpleNamespace

_logging.basicConfig(level=_logging.INFO)
LOGGER = _logging.getLogger("udi_interface_fallback")


class Custom(dict):
    def __init__(self, *args, **kwargs):
        super().__init__()


class Node:
    def __init__(self, *args, **kwargs):
        pass


udi_interface = SimpleNamespace(
    LOGGER=LOGGER,
    Custom=Custom,
    Node=Node,
)