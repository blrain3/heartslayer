from typing import List

from base_test_handler_fixture import BaseTestHandlerFixture
from heartslayer.ai.observant_heartslayer.observant_heartslayer import OBSERVANT_HEARTSLAYER
from heartslayer.machine.handlers.handler import Handler


class OhTestHandlerFixture(BaseTestHandlerFixture):
    strategy = OBSERVANT_HEARTSLAYER
    ai_handlers: List[Handler] = strategy.handlers
    slay_heart: bool = strategy.slay_heart
