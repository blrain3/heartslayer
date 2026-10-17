# CM 加固 v2 回执（静默抑制看门狗）
- 时间：2026-10-05 19:27:47
- 背景：第二次静默死锁复现（F59R3VP6YLV4，act3 商店；同族：净化流→购买→无响应）。现场取证：无异常抛出、mod 线程正常、bot 端同步阻塞读 → 判定为"状态发送被静默抑制"类（非异常类，v1 兜底不适用）。
- 改动（源树再备份见 pending）：
  1. GameStateListener.updateWedgeWatchdog()：① 命令已消费但 15s 无状态流 → registerStateChange() 借正常稳定判定管线补发（自节流、不会推瞬时状态）② blocked 卡死 >15s → 强制 resume。均打 WARN 日志（复发即可见+自愈）
  2. CommunicationMod.receivePostUpdate 每帧调用
- 构建：BUILD SUCCESS，jar 355,864B（+603B），class v52，串校验通过
- 指纹更新：launch-batch.sh -> e2d51ad02b3face3dd4cb83d；旧版备份 backup/CommunicationMod-emerald-hardened1-installed.jar
- 回滚：cp backup/CommunicationMod-emerald-hardened1-installed.jar /home/blrain/.local/share/Steam/steamapps/workshop/content/646570/2131373661/CommunicationMod.jar（并复位指纹）
- 另：'state' 命令=executeStateCommand 直接补发状态（bot 端自愈探测依据）；campfire/relic 阻塞补丁配对已复核
