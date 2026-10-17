from typing import List

from base_test_handler_fixture import BaseTestHandlerFixture
from heartslayer.ai.pwnder_my_orbs.pwnder_my_orbs import PWNDER_MY_ORBS
from heartslayer.machine.handlers.handler import Handler


class PmoTestHandlerFixture(BaseTestHandlerFixture):
    strategy = PWNDER_MY_ORBS
    ai_handlers: List[Handler] = strategy.handlers
    slay_heart: bool = strategy.slay_heart
