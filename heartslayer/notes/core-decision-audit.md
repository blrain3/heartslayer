# 核心决策链系统审计 — 进行中

> 只读审计，不改生产代码。每个发现按「问题 → 证据 → 影响 → 最小修复 → 测试 → 实战」顺序记录。
> 直到用户批准才进入修复；每个修复单独测试、单独实战验证、可回滚。
> 背景：Time Eater / Time Warp 修复已部署待实测（A1 一局未跑）；本审计与那次实测并列进行，互不影响。

## 0. 审计方法与可信度声明

方法一：源码证据（读实现 + 对比真实游戏机制）。
方法二：**端到端对拍**——用 A1 BHIIHETM25FA 的 Time Eater 战真实日志，逐 response 重建 state，
把 bot 实际发送的每条 `play` 命令原样喂回模拟器，比较模拟器终态 vs 游戏真实终态。
   - 回放脚本：`~/hermes-study/ascension-experiment/damage_crosscheck6.py`
   - 结果：**26 个出牌命令（T1–T5 全部），0 个 DIFF**（TE hp / block / player hp / player block 全对上）
   - 该 harness 复刻了生产 memory 链（`executor.py:40` 的 `HandlerAction.memory_book` 回传），
     不是共享对象，所以结论等价于"模拟器与真实游戏数值一致"。

### 踩坑记录（harness bug，不是 bot bug）
v1–v5 全部报 DIFF，根因全部在我的回放脚本，不在生产代码：
1. `BattleState` 没有 `play_card()`，正确的是 `transform_from_play((card_idx, target_idx), False)`。
2. memory book 不是共享对象：`game.py:76` 用 `action.memory_book` **替换**共享 book，
   `executor.py:40` 只在**第一条 play 之后**快照 `state.memory_general`。
   每命令新建一个共享 mb 会丢 WRATH / Mantra / Eruption 的增益，造成假 DIFF。
   → v6 修正后 26/26 全对。**结论：伤害链本身与真实游戏一致。**

---

## 1. 伤害判定 / 伤害计算

### 审计范围
- `rs/calculator/targets.py`（`inflict_damage`）
- `rs/calculator/battle_state.py`（block / power / stance / 多段修正）
- `rs/calculator/powers.py`、`card_effects.py`、`cards.py`

### 已验证一致的点（有源码 + 实测证据）
| 项 | 源码 | 结论 |
|---|---|---|
| Strength（玩家施压） | `battle_state.py:223` 在 `effect.damage` 上加 `powers.get(STRENGTH)` | 与游戏一致 |
| Vulnerable（打怪） | `targets.py:34` `damage *= 1.5` | 与游戏一致 |
| Vulnerable 多段 | 循环外乘一次、循环内每段用同一 damage | 与游戏一致（每段都吃） |
| Weak（受伤方） | `inflict_damage` 里按 `target.powers.get(WEAKENED)` | 与游戏一致 |
| Block 吸收 | `inflict_damage` 内先减 block 再减 HP | 与游戏一致 |
| **端到端** | 26 命令对拍 | **0 DIFF** |

### 疑点已逐行核对（结论：与游戏一致）
- `INTANGIBLE`：`targets.py:53-54` 对 INTANGIBLE_PLAYER / INTANGIBLE_ENEMY 双向 clamp 到 1。
  上游另有 5 个测试固化（`test_intangible_player_blocks_all_but_one_damage` 等）。
  stack 的按次衰减在模拟器里不建模，但 Watcher / bottled_ai 的对手里只有少数战斗（如 Awakened One / Intangible Boss）
  会带 Intangible，暂不构成 A1 主要矛盾 → **记录为已知建模边界，不列为问题**。
- `TORII`：`targets.py:73` `relics.get(TORII) and hit_damage < 6 → hit_damage = 1`，
  位于 `if hit_damage > 0:` 分支内（block 之后），1→1、2-5→1 → **与真实游戏一致**。
- `TUNGSTEN_ROD`：紧接 TORII 之后 `hit_damage -= 1` → 顺序与真实游戏一致。

**当前定性**：主伤害链（玩家→怪）在真实战斗中与游戏数值完全一致；INTANGIBLE 的 stack 衰减
是已声明的建模边界（模拟器刻意不建模部分对手 power 的时序/堆叠），不是本审计要修的缺口。
最强证据：`damage_crosscheck6.py` 对 A1 BHIIHETM25FA 的 Time Eater 战 **26 命令 0 DIFF**。

---

## 3. 药水、事件处理逻辑

### P1【问题｜中等置信】`Match and Keep!` 无法被识别 → 固定 `choose 0`，反复把诅咒装进牌组

> **重要更正（写于修复前，须与前述报错区分）**
> 我最初在审计里把 P1 定性为"`Event` 枚举与 CommunicationMod `event_id` 不匹配 → 一律降级 `choose 0`"，
> 并称 `Nest` 会"白掉 6 HP"。**该结论我已确认是误报，在此更正：**
> 1. `GameState.get_event()` 读的是 `screen_state['event_name']`，**不是 `event_id`**
>    （`rs/machine/state.py:205-211`）。
> 2. `event_name` 在**中文界面**下确实会被读成 `????`（编码丢失，见下）；
>    在**英文界面**下是规范名，全部命中枚举。本机 20 局日志是中文界面，
>    所以我看到的大面积 `????` 是**语言/编码现象，不是 id 命名不匹配**。
> 3. 我已经逐条核对了 41 个 `event_id` 与 `event_name` 的对应关系：`Nest→'The Nest'`、
>    `SensoryStone→'Sensory Stone'`、`FaceTrader→'Face Trader'`、`Designer→'Designer In-Spire'`、
>    `Beggar→'Old Beggar'`、`Drug Dealer→'Augmenter'`、`Ghosts→'Council of Ghosts'`、
>    `Accursed Blacksmith→'Ominous Forge'`、`Liars Game→'The Ssssserpent'`、`Transmorgrifier→'Transmogrifier'`
>    ——**这些都正确命中枚举并走各自的 case**。
>    → 所谓"Nest 白掉 6 HP"是我把多屏选项序列读串了；`THE_NEST` 的 case 本就是 `choose 0`（免费金币），
>    日志里那次 `[Stay in Line]` 出现在下一屏，不是盲选。
> 4. 因此：**`Nest`/`SensoryStone`/`FaceTrader`/`Golden Wing`(/`Wing Statue`) 不需要修**，
>    已有 case 都在正确工作。这次的真正目标只剩 **`Match and Keep!`**。

**真正的缺口（保留为 P1，范围收窄）**

`screen_state` 里有 `event_id`（英文内部 id，不受语言影响）和 `event_name`（本地化显示名，中文下变 `????`）。
`Match and Keep!` 的枚举值是 `"Match and Keep"`（**无感叹号**），所以：
- 英文界面：`event_name = "Match and Keep!"` → **不匹配** `"Match and Keep"` → 落 `case _` → `choose 0`
- 中文界面：`event_name = "????"` → 不匹配 → `choose 0`
  两条路都到 `choose 0`，`common_event_handler.py:129-130` 的 `case Event.MATCH_AND_KEEP` 是**死代码**。

**实际影响（真实日志，`action_getstate` 中英混合界面，A0 局）**
`~/hermes-study/ascension-experiment/` 内 `10H474B3AGLVI`、`13ZXNP114N09J`、`23CURD1U9V1R` 三局
完整记录了 Match and Keep 的 13 次连续选择：
```
choose 0 → card0 / card1 / Normality / Deep Breath / Normality / Deep Breath /
           Normality / Deep Breath / Normality / Deep Breath / [Leave]
```
一局里把 **5 张 Normality + 5 张 Deep Breath 装进牌组**：
- `Normality`：Watcher 打不出 Attack（本 strategy 核心就是出牌输出）→ 直接锁死攻击线
- `Deep Breath`：每回合开始固定扣 1 HP → 永久腐蚀，A1 下与"事件掉血"叠加恶化生存
**影响是确定且可累积的，不是随机运气问题。**

**能否复现**：能。fixture 可直接构造；`choice_list` 在中文界面下仍是英文小写卡名
（证据：`game_state['choice_list'] = ["normality","deep breath","card2",...]`），
所以识别路径在两种语言下都成立。

**关于"是否要同时补 `Event` 枚举值"——我的判断与边界建议（未替你拍板）**
补一个别的枚举值（如 `MATCH_AND_KEEP_ALT = "Match and Keep!"` 只能精确匹配一串英文字符串，
对中文界面下的 `????` **没有帮助**；而中文界面恰好是这台机器上跑的方式。
所以更稳的触发方式是**不看 `event_name`，改看 `event_id`**（`Match and Keep!` 恒定不受语言影响）。
这比往枚举里加同义值更能覆盖实际场景。
我倾向：(a) 在 `common_event_handler.py` 里把 `Event.MATCH_AND_KEEP` 的 case 改成读 `event_id` 或
读 `choice_list` 内容判断；(b) 归一到枚举仅作为公共常量。**但这会改动公共 handler 的行为，
爆炸半径超出"单点修复"，需要你确认范围（见对应对话中的两个待定问题）。**


---

## 4. 事件修复记录（Match and Keep!，单点、独立于 Time Warp）

### 用户批准的执行路径：**C → B**
先 TDD + helper/detection（C），再接 `common_event_handler` 公共路径让所有 strategy 受益（B）。
明确要求：不依赖本地化 `event_name`；Match and Keep 选择不固定 index；
Nest / Golden Wing / FaceTrader / SensoryStone **不碰**；不顺手重构其他事件。

### 审计纪律（本次误报换来的，长期有效）
**`event_id` / `event_name` / `choice_list` 是三个不同字段，绝不混用：**
1. `screen_state['event_id']`：英文内部 id，**不受语言影响** → 唯一可信的识别依据
   （`Match and Keep!` 恒为该值，日志已验证）。
2. `screen_state['event_name']`：**本地化显示名**，中文界面会变成 `????` → **不作为识别依据**。
3. `game_state['choice_list']`：英文小写卡名，两种语言下都可读 → 卡牌内容识别的依据。
`GameState.get_event()` 读的是 `event_name`（不是 `event_id`），所以枚举匹配天然带本地化风险。
**教训：不要把审计脚本读的字段直接当成生产代码读的字段。**

### 实现（改动清单，全部有测试与日志依据）
| 文件 | 改动 |
|---|---|
| `rs/common/handlers/common_event_handler.py` | 新增 `is_match_and_keep(state)`（只读 `event_id`）、`match_and_keep_choice(choice_list)`（跳过 `normality` / `deep breath`，绝不定死 index）；在 `find_event_choice` 的 `match` **之前**接公共路径，修掉原本是死代码的 `case Event.MATCH_AND_KEEP` |
| `tests/ai/common/handlers/test_match_and_keep.py` | 新增 18 个测试（识别 / 选择 / handler 集成） |
| `tests/res/event/event_match_and_keep_{english,chinese_ui,deep_breath_only,leave_only}.json` | 4 个 fixture，按仓库 `event_*` 命名惯例 |

**未做（明确记录，不是遗漏）**：没有给 `Event` 枚举补值（补同名字符串对中文界面 `????` 无效；
而 `event_id` 路径已能识别）→ 用户批准"不要简单增加 MATCH_AND_KEEP_ALT"。

### 关键设计点
- **`Deep Breath` 不是 Curse**：`get_card(CardId("deep breath")).card_type == CardType.SKILL`
  （已实测确认），所以只靠 `CardType.CURSE` 会漏掉它 → 名单必须显式列出，
  这也是 `cards_to_mass_discard` 等既有表没覆盖 Deep Breath 的原因。
- 面背牌以 `cardN` 占位名出现（日志 L117-162 实证）；选择逻辑对它们是稳定的、不会崩，
  但**不能假设它们是具体某张牌**，所以绝不为了"猜更好的牌"而重排。
- 只剩诅咒时退回第一张（该屏必须选，卡死比明知差的牌更糟）；无牌（仅 `leave`/空）返回 None，
  交给调用方原有默认行为（`handle()` 的 `len(choice_list)==1` 短路）。

### 测试结果
- 针对性：`18 tests OK`（TDD 先 RED：13 errors = 函数不存在、3 failures = handler 落在
  `choose 0` 即选中 Normality/Deep Breath；GREEN 后 18/18）
- 全量：**1193 tests OK（skipped=1）**，基线 1175 → **+18，零回归**

### 日志回放验证（`~/hermes-study/ascension-experiment/mk_replay.py`）
13 次 Match and Keep 选择逐条重放：**旧 bot 选了 8 次 Normality/Deep Breath，新逻辑 0 次**。
（更早一份记录里"13 次全来自 3 局"不准确：另两局在 `event_id` 规则下计 0 次，
13 次实际全部来自 `10H474B3AGLVI` 一局，已按实况更正。）

---

## 5. 状态标记（用户确认口径）
- **伤害计算：已验证，无需修改。** 端到端 26 条攻击命令 0 DIFF 是有效证据；不为了找问题继续改它。
- **药水：暂时观察，不为增加改动而改。**
- **事件处理：`Match and Keep!` 单点修复已完成（代码 + 18 测试 + 日志回放），待真实 A1 验证。**
  范围锁定，其他事件不重写；未 commit、未 PR。
- **Time Warp 修复保持不动**，与本次事件修复分开记录，方便之后分别比较实战效果。
- 下一步：部署到 `E:/Game/Steam/steamapps/common/SlayTheSpire/bottled_ai` 后跑真实 A1。
