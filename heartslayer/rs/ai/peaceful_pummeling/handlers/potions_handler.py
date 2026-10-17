from typing import List

from rs.game.screen_type import ScreenType
from rs.machine.command import Command
from rs.machine.handlers.handler import Handler
from rs.machine.handlers.handler_action import HandlerAction
from rs.machine.state import GameState

# see also common_combat_reward_handler.py for discarding potions
# these potions might still sneak into our slots with entropric brew
dont_play_potions = [
    'Smoke Bomb',
    'Elixir Potion',
    'Liquid Memories',
    'Snecko Oil',
    'Stance Potion',
    'Ambrosia',
    'Chaos Potion',
    'Distilled Chaos',
]

# 2026-10-05（社区笔记·P1' 同源问题）：非英文界面下 potion['name'] 会变成 "??"，
# 原按 name 的过滤会整体失效。改为“稳定 id 优先、显示名兜底”的双匹配。
def _normalize_potion_key(value: str) -> str:
    return (value or '').lower().replace(' ', '').replace('-', '').replace('_', '')

_DONT_PLAY_KEYS = {_normalize_potion_key(x) for x in dont_play_potions}

def is_dont_play_potion(pot: dict) -> bool:
    return _normalize_potion_key(pot.get('id') or pot.get('name')) in _DONT_PLAY_KEYS


class PotionsBaseHandler(Handler):

    def can_handle(self, state: GameState) -> bool:
        # must be implemented by children
        pass

    def handle(self, state: GameState, slay_heart: bool) -> HandlerAction:
        pot = self.get_potions_to_play(state)[0]
        wait_command = "wait 30"
        if pot['requires_target']:
            target = 0
            for m_index, monster in enumerate(state.get_monsters()):  # Find the back-est monster that isn't dead
                if (monster.get('id') or monster['name']) == 'Reptomancer':  # 2026-10-05 id 口径
                    target = m_index
                    break
                if not monster['is_gone']:
                    target = m_index
            return HandlerAction(commands=[wait_command, "potion use " + str(pot['idx']) + " " + str(target), wait_command])
        return HandlerAction(commands=[wait_command, "potion use " + str(pot['idx']), wait_command])

    def get_potions_to_play(self, state: GameState) -> List[dict]:
        to_play = []
        for idx, pot in enumerate(state.get_potions()):
            if pot['can_use'] and not is_dont_play_potion(pot):
                pot['idx'] = idx
                to_play.append(pot)
        return to_play


class PotionsEliteHandler(PotionsBaseHandler):
    def __int__(self):
        super().__init__()

    def can_handle(self, state: GameState) -> bool:
        hp_per = state.get_player_health_percentage() * 100
        alive_monsters = len([m for m in state.get_monsters() if not m.get('is_gone')])
        # 2026-10-05（社区笔记：多敌战/精英不吝惜药水）：原仅 hp<=50；多敌(>=3) 时放宽到 75
        return state.has_command(Command.POTION) \
               and state.combat_state() \
               and state.screen_type() == ScreenType.NONE.value \
               and state.game_state()['room_type'] == "MonsterRoomElite" \
               and state.combat_state()['turn'] == 1 \
               and (hp_per <= 50 or (hp_per <= 75 and alive_monsters >= 3)) \
               and self.get_potions_to_play(state)


class PotionsEventFightHandler(PotionsBaseHandler):  # Treat most Event Fights like Elites
    def __int__(self):
        super().__init__()

    def can_handle(self, state: GameState) -> bool:
        hp_per = state.get_player_health_percentage() * 100
        return state.has_command(Command.POTION) \
               and state.combat_state() \
               and state.screen_type() == ScreenType.NONE.value \
               and state.game_state()['room_type'] == "EventRoom" \
               and not state.has_monster("FungiBeast") \
               and (hp_per <= 50 and state.combat_state()['turn'] == 1) \
               and self.get_potions_to_play(state)


class PotionsBossHandler(PotionsBaseHandler):
    def __int__(self):
        super().__init__()

    def can_handle(self, state: GameState) -> bool:
        return state.has_command(Command.POTION) \
               and state.combat_state() \
               and state.screen_type() == ScreenType.NONE.value \
               and state.game_state()['room_type'] == "MonsterRoomBoss" \
               and state.combat_state()['turn'] == 1 \
               and self.get_potions_to_play(state)
