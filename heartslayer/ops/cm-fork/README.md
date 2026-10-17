# CM fork 加固补丁
CommunicationMod 自建版（master+PR#20 + 本地加固）的补丁存档：
- 20261005-hardening-wedge-fix.patch：
  1) 命令执行兜底 catch（异常→记日志+强制补发状态，杜绝静默挂起）
  2) makeShopScreenChoice 索引越界守护
  构建：maven+JDK8；应用方法：cd CommunicationMod && git apply <patch> && mvn -DskipTests package
