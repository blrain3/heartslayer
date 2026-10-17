from typing import Callable, Optional

from heartslayer.calculator.interfaces.battle_state_interface import BattleStateInterface
from heartslayer.calculator.interfaces.card_effects_interface import CardEffectsInterface
from heartslayer.calculator.interfaces.card_interface import CardInterface

CardEffectCustomHook = Callable[[BattleStateInterface, Optional[CardEffectsInterface], Optional[CardInterface], Optional[int]], None]
CardEffectCustomHookWithCard = Callable[[CardInterface], None]
