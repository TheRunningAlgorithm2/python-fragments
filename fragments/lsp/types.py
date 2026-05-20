from lsprotocol.types import REQUESTS, NOTIFICATIONS
from typing import Callable, Coroutine, Any, TypeAlias

HandlerFunc: TypeAlias = Callable[[REQUESTS | NOTIFICATIONS], Coroutine[Any, Any, None]]
