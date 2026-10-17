from typing import List

from base_test_handler_fixture import BaseTestHandlerFixture
from heartslayer.ai._example.example import EXAMPLE_STRATEGY
from heartslayer.machine.handlers.handler import Handler


class CoTestHandlerFixture(BaseTestHandlerFixture):
    strategy = EXAMPLE_STRATEGY
    ai_handlers: List[Handler] = strategy.handlers
    slay_heart: bool = strategy.slay_heart
