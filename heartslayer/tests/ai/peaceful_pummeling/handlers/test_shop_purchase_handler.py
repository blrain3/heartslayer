from ai.peaceful_pummeling.pp_test_handler_fixture import PpTestHandlerFixture
from heartslayer.ai.peaceful_pummeling.handlers.shop_purchase_handler import ShopPurchaseHandler


class ShopPurchaseHandlerTestCase(PpTestHandlerFixture):
    handler = ShopPurchaseHandler

    def test_buy_lantern_in_localized_shop(self):
        # zh 界面：choice_list 里名字是 "??"；靠 下标直算（purge 位 + 可负担顺序）买 Lantern
        self.execute_handler_tests('shop/shop_zh_buy_lantern.json', ['choose 9', 'wait 30'])

    def test_buy_potion_in_localized_shop(self):
        # 其他目标均不可得时，按 DESIRED_POTIONS 顺序买下 Fruit Juice
        self.execute_handler_tests('shop/shop_zh_buy_potion.json', ['choose 11', 'wait 30'])

    def test_skip_potion_when_slots_full(self):
        # 三个药水槽都占满 → 不买药水，直接离开
        self.execute_handler_tests('shop/shop_zh_potion_slots_full.json', ['return', 'proceed'])
