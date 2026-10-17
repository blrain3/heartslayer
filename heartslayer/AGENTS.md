# AGENTS.md — bottled_ai (研究副本) 工作规则

本文件是你（coding agent）在这个仓库里的常驻规则。任何修改前先读完它。

## 0. 这个仓库在做什么

一个跑《杀戮尖塔》(Slay the Spire) 的 bot（`bottled_ai`），通过 CommunicationMod 收发游戏状态。
目标不是"写出漂亮的代码"，而是**让 bot 在 A1（Ascension 1）真的变强**，判断以实测为准。

本副本在 Linux 迁移后同时承担运行职责（研究 + 运行同一副本）：
- 运行方式：游戏目录中的符号链接 `bottled_ai` 直接指向本仓库（`~/projects/bottled_ai`），游戏侧日志/运行数据即来自本副本（旧 Windows 部署路径 `E:/Game/...` 已废弃）
- 未 commit、未 PR；上游基线是 `7b47a87`
- 运行产物（logs/、runs/ 等）可以读；修改生产代码仍按下方红线流程走

## 1. 绝对红线（违反即任务失败）

1. **不 commit、不 push、不 PR、不 merge、不改 git 历史。** 用户会自己拍板。
2. **不改动以下常量与全局状态**：global `default_comparisons`、strategy/priority、seed、
   run_amount、CommunicationMod 的命令行参数。Ascension 默认 0 不许改。
3. **不动这些方向**（已结案或明确冻结）：
   - 伤害计算（`rs/calculator/`）：**已验证与游戏一致**（26 条攻击命令端到端 0 DIFF），
     不许"为了找问题"去改它。
   - 药水逻辑：只观察，不调整。
   - `Event` 枚举：不加同义值。
   - Nest / Golden Wing / FaceTrader / SensoryStone 的事件处理：确认正常，不碰。
   - Time Warp 修复（`time_eater_comparator.py` + `least_time_warp_risk`）：
     保持不动，与事件修复分开记录，方便分别比较实战效果。
4. **不要一次性大重构。** 每个修复单独成 patch、单独测试、单独实战验证、可回滚。
5. **只读审计时不许改生产代码。** 先出证据（源码位置 / 触发条件 / 实际影响 / 能否复现），
   等批准再动手。

## 2. 怎么验证（不要只跑测试就算完）

- 单测：`python -m unittest discover -s ./tests/ -t ./tests`（基线 1196 tests OK, skipped=1）
- 针对性：`python -m unittest discover -s ./tests/ -t ./tests -k <关键字>`
- **实战验证**：从 `E:/Game/Steam/steamapps/common/SlayTheSpire/bottled_ai/logs/runs/` 的
  真实日志回放。回放必须能指出"旧的会怎样、新的会怎样"，而不是只报"通过"。
- 报告结论时**区分证据强度**：源码推断 / 单测覆盖 / 真实日志实测，三者不要混为一谈。
- 不要用命令的 exit code 当成"生效了"的证据。要找到**独立的、可复核的证据**。

## 3. 事件处理的三个字段（别再混）

`screen_state` / `game_state` 里有三个不同东西：

| 字段 | 含义 | 可否作识别依据 |
|---|---|---|
| `screen_state['event_id']` | 英文内部 id，**不受语言影响** | ✅ 唯一可信 |
| `screen_state['event_name']` | 本地化显示名，中文界面变 `????` | ❌ 不可 |
| `game_state['choice_list']` | 英文小写卡名，两种语言下都可读 | ✅ 卡牌内容识别用 |

`GameState.get_event()` 读的是 `event_name`（`rs/machine/state.py:205-211`），
所以基于 `Event` 枚举的 `match` 天生带本地化风险。
历史教训：曾把审计脚本读的字段当成生产代码读的字段，得出过误报，**已在
`notes/core-decision-audit.md` 书面更正**。

## 4. 当前进行中的工作

Match and Keep! 事件修复（识别 + 回避 Normality / Deep Breath），
记录在 `notes/core-decision-audit.md` 第 4 节。
- 相关文件：`rs/common/handlers/common_event_handler.py`、
  `tests/ai/common/handlers/test_match_and_keep.py`、
  `tests/res/event/event_match_and_keep_*.json`
- patch：`~/hermes-study/ascension-experiment/event-match-and-keep.patch`（纯新增，可一键回滚）

**Watcher（观者）是当前重点角色。**

## 5. 拿不准时

停下来问，不要替用户拍设计决定。宁可多问，不要猜。
