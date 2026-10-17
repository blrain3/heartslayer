# Match and Keep 第二个问题：低价值/废牌选择

用户要求：先源码+历史日志确认（不要直接改），确认是真实策略缺口再做最小修复。

## 1. Match and Keep 当前到底有哪些合法选择

每屏 `choice_list` 的元素分三类（实机 10XDXJRPAI4XR 第 41 层 12 屏实测 + NI5X0FGD1WW1 实测）：

| 形式 | 含义 | 例子 |
|------|------|------|
| `cardN` | 面背，未翻开 | `card0`...`card11` |
| 英文牌名 | 已翻开 | `flyingsleeaves`, `judgement`, `bowlingbash`, `battlehymn` |
| `leave` | 离开 | 最后一屏 |

**关键机制发现（此前未知）**：配对成功后，已翻开的牌对**会重新回到列表**。
证据：实机 log L2693 装走 flyingsleeves → L2698 列表里 judgement 仍在 →
L2703 flyingsleeaves 又出现。所以这 12 屏不是"12 张不同的牌"，而是
**同一对可无限次获取**。这是 bot 拿到 5×judgement + 5×flyingsleeaves 的直接原因。

## 2. 为什么原逻辑会选这些牌

原实现（本次修改前）：

```python
for idx, choice in enumerate(choice_list):
    name = normalize(choice)
    if not name or name == "leave": continue
    if first_card_index is None: first_card_index = idx
    if name not in match_and_keep_unwanted_cards:   # 只排除 normality / deep breath
        return idx
```

`judgement` / `flyingsleeaves` 都不在黑名单里 → 每次遇到这对就返回 index 0。
**必然结果，不是运气**：只要这一对先翻开，就会被一直选。

## 3. 是否已有未被利用的牌价值判断

有，而且 handler 早就拿到了：

- `CommonEventHandler.__init__(self, removal_priority_list, cards_desired_for_deck)`
  —— `self.cards_desired_for_deck` 一直存在，Match and Keep 分支没有用它。
- 可复用范式在 `rs/common/handlers/card_reward/common_card_reward_handler.py`：
  ① 只取 `desired` 里的牌；② **看牌组里已有几张**，够了就不再要；
  ③ 用 `state.get_deck_card_list_by_name_with_upgrade_stripped()` 拿牌组统计。

归一化一致性（已逐行核对）：
`state.py:154-163` deck 键 = `card.name.replace("+","").lower()`，
我 helper 内 = `str(choice).strip().lower().replace("+","")`。两边等价。

## 4. 最小修复：四层优先级

不硬编码任何具体牌名（除诅咒黑名单），全部复用策略已有数据：

1. `cards_desired_for_deck` 里想要、且牌组张数还没达标的牌（最优）
2. 面背 `cardN`（未知，可能正是想要的）
3. 已知但不想要的牌（屏幕强制选，退而求其次）
4. 诅咒（仅当前面全空时）

签名保持向后兼容（新参数可选），`handler` 调用处传入 strategy 表 + 实时牌组统计。

## 5. 测试与回放

- 新增 `tests/ai/common/handlers/test_match_and_keep_value.py`（9 个：优先级/达标跳过/面背优先/保底/兼容旧调用/handler 传参）
- 新增 `tests/ai/common/handlers/test_match_and_keep_replay.py`（5 个：真实 13 屏回放，0 诅咒、面背优先、junk 上界、牌组不塞满、不复现 5×+5×）
- 全量：研究副本 **1210 OK skipped=1**；部署副本同为 **1210 OK**（基线 1196）
- 回放实机 13 屏：新逻辑 13 次选择 = `card0` ×2 + `card2` ×10 + leave，**junk 添加 0 张**（旧逻辑 12 张全垃圾）

## 6. 一个自我更正（重要，保留记录）

我一度认为"中文界面下 choice_list 牌名变 `??`，导致黑名单失效"。
**该判断错误**，依据：

1. 同一份日志里 `deck[].name` 也是 `??`，但 `deck[].id` 是 `Strike_P`/`Defend_P`
   → 日志写入时把非 ASCII 统一替换成 `?`，不是 choice_list 特有现象；
2. 上游 `common_card_reward_handler` **完全没有本地化处理**，直接用 `choice_list`
   里的名字匹配英文 `DESIRED_CARDS_FOR_DECK`。若中文界面真返回中文牌名，
   上游选牌逻辑早就失效，而它跑了 14 局中文局并未失效；
3. `bowlingbash` / `battlehymn` 等 ASCII 牌名在同局正常出现。

**结论：日志的 `?` 是编码损坏，bot 实际收到的是语言无关 id。** 中文缺口的担忧作废，
等下一局中文局自然出现 Match and Keep 再补实机闭环（不人为挑 seed）。

## 7. 顺带发现（记录，不动，不在本次范围）

`rs/machine/state.py:64-68` `get_choice_list_upgrade_stripped_from_choice()`
**原地修改** `self.game_state()` 返回的 `choice_list`（`choice_list_modified[idx] = ...`），
会污染共享状态。任何调用它的 handler 都会留下去除 `+` 后的列表。
本次修复刻意不调用它，因此不受影响；修复时仍自行归一化。
