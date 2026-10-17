# heart-batch 运营脚本（笔记本本地）
碎心批次的守护式运营工具（本目录为版本化副本，运行主场在 ~/hermes-study/heart-loop-valid-20261005/）。

- launch-batch.sh [局数] [--dry-run]：CM 指纹/残留/Steam 登录/模组数四重门控 → 启 MTS → OCR 点击 → 拉起守望器与卡死看护
- stop-batch.sh [--all]：bot→游戏→units 顺序停止（--all 含卡死看护）
- watchdog-stuck.sh：bot 存活且日志 >180s 无写入（双采样）→ 止损 + 自动重开（上限 5 次）
- watch-milestones.sh：心脏战里程碑记录（emerald/sapphire/recall/心脏/胜利）
- verify_live_run.py <log>：逐回合余能/出牌/低效标记 + 新旧 comparator 决策对照 + 预算越界检查
- check-shops.py [logs...]：商店采购核对（价格 vs 扣金）
- status.sh：一览当前对局状态

注：路径按笔记本约定写死（~/projects/bottled_ai、~/hermes-study/...），换机需改 P/S/JAR 常量。
