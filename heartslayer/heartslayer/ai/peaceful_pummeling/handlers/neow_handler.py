from heartslayer.common.handlers.common_neow_handler import CommonNeowHandler


class NeowHandler(CommonNeowHandler):

    def __init__(self):
        super().__init__(desired_choices=[
            # 2026-10-05 重排（社区实践：删/变/金币优先；换 Boss 遗物下调到末位）
            # 注意：非英文界面下此列表尚无法命中（choice_list 被本地化），属 P1′/专项修复后才能生效
            'remove a card from your deck',
            'transform a card',
            'obtain 100 gold',
            'upgrade a card',
            'obtain a random common relic',
            'choose a card to obtain',
            'obtain 3 random potions',
            'enemies in your next three combats have 1 hp',
            'max hp +8',
            'obtain a random rare card',
            'choose a colorless card to obtain',
            'lose your starting relic obtain a random boss relic',
        ])

