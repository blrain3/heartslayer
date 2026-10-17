# Time Eater (Act 3 Boss) 战斗复判记录 — A1 seed BHIIHETM25FA

- 记录日期: 2026-09-23
- 分析对象: `logs/runs/2026-09-23-10-22-56--BHIIHETM25FA.log`（Watcher / Ascension 1）
- 分析方式: 只读分析 + OpenCode 辅助验证，**未修改任何生产代码**
- 结论状态: 停在验证阶段，未修复、未提 PR、未跑 A2

---

## 1. A1 两局结果与 A0 对照

| Seed | Ascension | 最终 floor | Score | 结局 | 死因 | 异常 |
|---|---|---|---|---|---|---|
| Q3HKXFBU1VYS | 1 | 21 | 247 | 败北 | Sentry + Spheric Guardian（Act 1 精英） | 无 |
| BHIIHETM25FA | 1 | 50 | 565 | 败北 | **Time Eater（Act 3 boss）** | 无 |

A0 对照组（同策略 PEACEFUL_PUMMELING / Watcher）：

| Seed | Ascension | 最终 floor | Score | 结局 |
|---|---|---|---|---|
| K2W07AC1TX09 | 0 | 51 | 686 | 通关（Victory） |
| T3EJB96DEUIH | 0 | 51 | 724 | 通关（Victory） |

两局 A1 均零异常（Traceback / Exception / KeyError / UnicodeEncodeError / `"error"` 全部为 0），
有完整 run_history 战绩行，走正常终局路径。

---

## 2. H1 / H2 / H3 复判结论

初始分析（本记录之前的判断）给出三个假设，经源码 + 日志复盘后修正如下。

### H1「Time Warp 没有被有效管理」→ **部分否定**

机制**存在且生效**，只是有刻意保留的建模边界：

- `rs/calculator/battle_state.py:1099-1101`
  ```python
  if monster.powers.get(PowerId.TIME_WARP, 0) >= 12 and not self.time_warp_full:
      self.time_warp_full = True
  ```
- `rs/calculator/battle_state.py:70`（`get_plays`）与 `:185`（`repeat_card`）在
  `is_turn_forced_to_be_over()` 为真时**直接返回空 / 不再出牌**，即 warp 到 12 后模拟停止生成后续出牌。
- `rs/calculator/battle_state.py:419-420`：每打一张牌 `add_powers({TIME_WARP: 1})` 正确递增。

原判断「Time Warp 完全没被管理」错误，已作废。

### H2「`max(2, damage)` 抹平了 A1 的伤害差异」→ **否定**

- `rs/common/comparators/core/comparisons.py:69-71`
  ```python
  def least_incoming_damage_over_1(best: CA, challenger: CA) -> Optional[bool]:
      return None if max(2, best.incoming_damage()) == max(2, challenger.incoming_damage()) \
          else challenger.incoming_damage() < best.incoming_damage()
  ```
- 该函数只把 **≤2 的伤害**折叠成平局；3 vs 10 依然能比出大小。
- 上一轮「A1 下 15 伤被抹平」的推断**错误**，已作废。
- 该行为已由新增测试 `test_least_incoming_damage_over_1_compares_three_against_ten` 固化。

### H3「T3 只打一张牌是比较器排序缺陷 / BFS 没搜到更好路径」→ **否定**

T3 的少出牌是 **warp=11 位置造成的 trap**，不是决策缺陷：

1. T2 结束时 warp = 11（见 §3 证据）。
2. T3 手牌为 CrushJoints / Vigilance / Ragnarok / BattleHymn，能量 4，日志显示只发 `play 2`（Vigilance）后 `end`。
3. warp = 11 意味着**再打任何一张牌，第 12 张就触发 Time Warp**（回合并打 +2 Strength）；
   而 `end` 会让 T4 挨敌人的回合伤害。两害相权，bot 选择了 `end`。
4. `time_warp_full` 机制把 T3 的出牌空间压成「只打 0 张」或「打满到 12 张」，
   中间没有好的可行解——这是机制约束，不是搜索失败。

---

## 3. T2/T3 warp=11 关键证据（逐行取自原日志，非按回合牌数推断）

日志中 Time Eater 的 `powers` 每个 response 均含 `Time Warp` 计数器
（格式 `{"amount":N,"name":"Time Warp","id":"Time Warp"}`），完整轨迹：

```
L2242 T1 warp=0    PHP 59  TEhp 456
L2253 T1 warp=1    PHP 59  TEhp 456
L2257 T1 warp=2    PHP 59  TEhp 456
L2261 T1 warp=3    PHP 59  TEhp 456
L2265 T1 warp=4    PHP 59  TEhp 438
L2269 T1 warp=5    PHP 59  TEhp 408
L2273 T1 warp=6    PHP 59  TEhp 339
L2277 T1 warp=7    PHP 59  TEhp 339
L2281 T1 warp=8    PHP 59  TEhp 339   <- T1 结束（发了 end）
L2284 T2 warp=8    PHP 44  TEhp 339   <- T2 起始已掉 15（T1 end-of-turn，非 warp 触发）
L2288 T2 warp=9    PHP 44  TEhp 339
L2292 T2 warp=10   PHP 44  TEhp 315
L2296 T2 warp=11   PHP 44  TEhp 315   <- T2 结束
L2299 T3 warp=11   PHP 44  TEhp 315   <- T3 起始：掉 15（29->见下），Str 1->3（warp 触发）
L2303 T4 warp=0    PHP 29  TEhp 315   <- T4 起始，warp 重置为 0
...
L2327 T4 warp=6    PHP 29  TEhp 267   <- T4 结束
L2330 T5 warp=6    PHP 29  TEhp 267
L2350 T5 warp=11   PHP 31  TEhp 240
L2354 T5 warp=0    PHP 0   TEhp 231   <- 第 12 张触发 warp，死亡
```

对应命令流（原日志 `Sending message` 行，T2→T3 段）：

```
L2291 play 1 0   -> warp 10
L2295 play 1     -> warp 11
L2298 end        -> T3 起始 warp 11, PHP 44
L2302 play 2     -> T4 起始 warp 0,  PHP 29（warp 在第 12 张触发：-15, Str +2）
```

**关键点**：warp 从 0→11 逐张可见，两次触发（T3 起始、T5 末尾）都可与 PHP 下降一一对应，
不是按回合牌数推断出来的。

---

## 4. Time Warp 的模拟器建模边界

- **已建模**：计数器递增（`battle_state.py:419-420`）；warp ≥12 时强制回合结束、
  停止生成出牌（`battle_state.py:1099-1108`）。
- **未建模**：warp 触发时的 **+2 Strength** 与**回合并打伤害**。
  这一点在源码里有明确的刻意说明：
  `rs/calculator/enums/power_id.py:121`
  > `TIME_WARP = 'time warp'  # We currently ignore the Strength-up from Time Warp because that might trigger too-conservative battle decisions with current decision-making.`

- **后果**：bot 知道「该收手」，但不知道「不收手的代价具体多少」。
  这使 `avoid_inconvenient_time_warp` 只能在 0/1 二值上工作，无法评估
  「再打一张牌换更多伤害是否值得」这类连续权衡。

---

## 5. 次要观察（非缺陷，仅记录）

- `rs/common/comparators/core/assessment.py:260-268` 的 `inconvenient_time_warp_count()`
  只把 warp == 10 或 11 标记为 bad。真正值得提前收手的窗口（8/9）未覆盖；
  且在 `rs/common/comparators/big_fight_comparator.py:8` 中
  `avoid_inconvenient_time_warp` 被插在 `least_incoming_damage_over_1` **之后**，
  优先级低于伤害比较。
- 以上两点是**设计取向**，不是代码错误；修改它们会波及共享比较器（见 §7），本次不改。

---

## 6. 定性结论

**不是已有逻辑缺陷，不是比较器排序 bug，也不是随机性 / 牌序。**

真正原因是三件事叠加：

1. **数值层面**：A1 的伤害抬升 + warp 触发的 +2 Strength，使 Time Warp 两次触发造成约 30 点
   HP 损失 + Str 从 1 涨到 5。同一策略在 A0 的容错预算被击穿（A0 两局 Floor 51 通关，
   A1 两局只到 21 与 50）。
2. **策略层面**：`inconvenient_time_warp_count` 的窗口（仅 10/11）与优先级位置，
   恰好让「最该提前收手」的场景（warp 8/9）失效。
3. **工程层面**：模拟器刻意不建模 warp 触发效果（有意决策，见 §4），反过来限制了
   比较器做更细的权衡。

最小修改点**暂不实施**：任何对 `default_comparisons` 排序或
`least_incoming_damage_over_1` 全局行为的改动都会影响所有角色的所有战斗，
风险与收益不匹配。下一步如需继续，应优先讨论「如何低风险观测 / 建模 Time Warp 代价」，
而不是直接调参。

---

## 7. 爆炸半径（改动前必须评估）

| 目标 | 影响范围 |
|---|---|
| `rs/common/comparators/core/comparisons.py` 内的任一比较函数 | **全部角色、全部战斗**（`default_comparisons` 全局共享） |
| `rs/common/comparators/common_general_comparator.py:13` 的 `default_comparisons` 顺序 | 全部角色、全部战斗 |
| `rs/common/comparators/big_fight_comparator.py` | floor 33 / floor 50 的 big fight（继承自全局列表） |
| `rs/calculator/battle_state.py` 的 warp 建模 | 全部战斗的模拟正确性，且违背 `power_id.py:121` 记录的有意决策 |

---

## 8. 仓库当前状态与测试清单

git status（截至记录时）：

```
 M tests/calculator/test_calculator_powers.py
?? tests/ai/common/comparators/test_comparison_functions.py
```

**只有测试文件变更，无任何生产代码改动。**

### OpenCode 新增/修改的测试

| 路径 | 类型 | 测试名 |
|---|---|---|
| `tests/ai/common/comparators/test_comparison_functions.py` | 新增文件（untracked） | `test_least_incoming_damage_over_1_compares_three_against_ten` |
| | | `test_least_incoming_damage_over_1_flattens_only_values_of_two_or_less` |
| | | `test_inconvenient_time_warp_count_is_true_only_when_time_warp_is_ten_or_eleven` |
| | | `test_avoid_inconvenient_time_warp_prefers_count_outside_ten_or_eleven` |
| `tests/calculator/test_calculator_powers.py` | 修改（append 到 `CalculatorPowersTest`） | `test_time_warp_does_not_reset_or_apply_strength_on_trigger` |
| | | `test_time_warp_trigger_effects_are_not_applied_at_end_turn` |

新增测试意图：

- 前 4 个固化「比较函数当前行为」，使未来任何参数/排序改动立刻可见回归。
- 后 2 个显式断言**模拟器当前不建模** warp 触发效果（counter 只递增到 12，
  Strength 不变，`end_turn()` 也不应用），把 §4 的建模缺口变成可执行契约。
  将来若补上建模，这两个测试会失败并提示人工复核，属预期。

### 测试结果

```
$ python -m unittest discover -s ./tests/
Ran 1158 tests in 0.311s
OK (skipped=1)
```

基线为 1152，本次新增/修改后为 **1158 tests OK, skipped=1**。

---

## 9. 上游已有的相关用例（回溯线索）

仓库自带两个 Time Eater 专用 fixture，说明作者已考虑该机制：

- `tests/res/battles/specific_comparator_cases/big_fight/time_eater_play_more_to_avoid_inconvenient_time_warp.json`
  → `tests/ai/common/handlers/test_battle_handler.py:413` `test_play_more_to_avoid_awkward_time_warp`
- `tests/res/battles/specific_comparator_cases/big_fight/time_eater_play_less_to_avoid_inconvenient_time_warp.json`
  → `tests/ai/common/handlers/test_battle_handler.py:418` `test_play_less_to_avoid_awkward_time_warp`

后续若要改 warp 相关逻辑，这两个用例是最小回归集。

---

## 10. 下一步（未开始，需先讨论）

**议题：如何低风险观测 / 建模 Time Warp 代价。**

方向：只增加「可观测量」，不改比较逻辑与排序——例如让模拟器或比较器能读到
「继续出牌将触发 warp 的估计代价」，而非直接调整 `default_comparisons` 顺序或
`least_incoming_damage_over_1` 的归一化基数。

**明确不做**：不跑 A2；不修改 `default_comparisons` 或全局 comparator 排序；
不改 strategy / priority / ascension 配置；不提 PR、不 commit。

---

## 附：A1 ascension 实验补丁（保留）

Ascension 实验补丁继续保留，回滚命令（一键恢复 A0 默认路径）：

```
git checkout -- main.py rs/machine/game.py
```

补丁存证：

- `~/hermes-study/ascension-experiment/game.py-ascension.patch`
- `~/hermes-study/ascension-experiment/main.py-a1-experiment.patch`
- `~/hermes-study/ascension-experiment/pre-existing-patches.diff`
