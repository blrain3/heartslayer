from presentation_config import presentation_mode, p_delay, p_delay_s
from rs.ai.peaceful_pummeling.config import CARD_REMOVAL_PRIORITY_LIST, DESIRED_POTIONS
from rs.game.screen_type import ScreenType
from rs.machine.handlers.handler import Handler
from rs.machine.handlers.handler_action import HandlerAction
from rs.machine.state import GameState


class ShopPurchaseHandler(Handler):

    def __init__(self):
        self.relics = [
            'Pen Nib',
            'Bag of Marbles',
            'Shuriken',
            'Meat on the Bone',
            'Vajra',
            'Bag of Preparation',
            'Kunai',
            'Eternal Feather',
            'Regal Pillow',
            'Lee’s Waffle',
            'Meal Ticket',
            'Strawberry',
            'Pear',
            'Pantograph',
            'Anchor',
            'Horn Cleat',
            'Lantern',
            'Centennial Puzzle',
            'Damaru',
        ]

        # (id, cap) —— cap 与 config 目标张数一致；2026-10-05 扩表（id 均经 runs 日志核验）
        self.cards = [
            # Blasphemy 有单独的优先购买分支（见 find_choice 第 3 步）
            ('Adaptation', 2),      # Rushdown
            ('Mentalfortress', 2),  # Mental Fortress
            ('Scrawl', 1),          # 潦草急就
            ('TalkToTheHand', 3),   # 以手拒之
            ('InnerPeace', 2),      # 内心宁静
            ('FearNoEvil', 2),      # 不惧妖邪
            ('Tantrum', 2),         # 发泄
            ('EmptyMind', 1),       # 化智为空
        ]

    def can_handle(self, state: GameState) -> bool:
        return state.screen_type() == ScreenType.SHOP_SCREEN.value

    def handle(self, state: GameState, slay_heart: bool) -> HandlerAction:
        choice = self.find_choice(state)
        idx = None
        if choice == "purge":
            # choice_list 首项是英文字面量 "purge"（两种语言下不变）
            try:
                idx = state.get_choice_list().index("purge")
            except ValueError:
                idx = None
        elif choice:
            # 2026-10-05 下标直算（runs 日志 16 例核验）；不再依赖 name（zh 下 name="??" 会错配/失效）
            idx = self.find_item_index(state, choice)
        if choice and idx is not None:
            if presentation_mode:
                return HandlerAction(commands=[p_delay, "choose " + str(idx), p_delay_s, "wait 30"])
            return HandlerAction(commands=["choose " + str(idx), "wait 30"])
        if presentation_mode:
            return HandlerAction(commands=["wait " + p_delay, "return", "proceed"])
        return HandlerAction(commands=["return", "proceed"])

    def find_choice(self, state: GameState):
        gold = state.game_state()['gold']
        screen_state = state.game_state()['screen_state']
        can_purge = screen_state['purge_available'] and gold >= screen_state['purge_cost']

        # 1. Purge curses
        if can_purge and state.deck.contains_curses_we_can_remove():
            return "purge"

        # 2. Membership Card（id/name 归一化匹配，zh 下 name 报废也能命中）
        for relic in screen_state['relics']:
            if self._matches(relic, 'Membership Card') and gold >= relic['price']:
                return relic

        # 3. Blasphemy（id 判定；返回物品 dict，由 handle 直算下标）
        for card in screen_state['cards']:
            if card['id'] == 'Blasphemy' and gold >= card['price']:
                return card

        # 4. Relics based on list
        for p in self.relics:
            for relic in screen_state['relics']:
                if self._matches(relic, p) and gold >= relic['price']:
                    return relic

        # 5. Cards based on list（2026-10-05：修 p.lower 误用并加张数上限）
        deck_card_list = state.get_deck_card_list_by_id()
        for card_id, cap in self.cards:
            for card in screen_state['cards']:
                if card['id'] == card_id and gold >= card['price'] \
                        and deck_card_list.get(card_id.lower(), 0) < cap:
                    return card

        # 6. Purge in general
        if can_purge and state.deck.contains_cards(CARD_REMOVAL_PRIORITY_LIST):
            return "purge"

        # 7. Potions（2026-10-05 商店购药：有空槽位、买得起、未持有时，按 DESIRED_POTIONS 顺序买）
        if self._has_free_potion_slot(state):
            held = [self._norm(p.get('id', '')) for p in state.get_potions()]
            for wanted in DESIRED_POTIONS:
                for potion in screen_state.get('potions', []):
                    if self._norm(potion.get('id', '')) == self._norm(wanted) \
                            and gold >= potion['price'] \
                            and self._norm(wanted) not in held:
                        return potion

        # Nothing we want / can afford, leave.
        return ''

    def find_item_index(self, state: GameState, item):
        """choice_list 下标直算：purge 位(0/1) + 买得起列表中的位置。
        顺序 cards→relics→potions；只计 price<=gold 的条目。
        （2026-10-05 经真实 runs 日志 16 例核验：cl = [purge?] + [价格可负担的物品]）"""
        gold = state.game_state()['gold']
        screen_state = state.game_state()['screen_state']
        can_purge = screen_state['purge_available'] and gold >= screen_state['purge_cost']
        affordable = [x for key in ('cards', 'relics', 'potions')
                      for x in screen_state.get(key, [])
                      if x.get('price', 10 ** 9) <= gold]
        try:
            return (1 if can_purge else 0) + affordable.index(item)
        except ValueError:
            return None

    @staticmethod
    def _norm(text: str) -> str:
        return text.lower().replace(' ', '')

    def _matches(self, item, wanted: str) -> bool:
        return self._norm(item.get('id', '')) == self._norm(wanted) \
            or self._norm(item.get('name', '')) == self._norm(wanted)

    def _has_free_potion_slot(self, state: GameState) -> bool:
        return any(p.get('id') == 'Potion Slot' for p in state.get_potions())
