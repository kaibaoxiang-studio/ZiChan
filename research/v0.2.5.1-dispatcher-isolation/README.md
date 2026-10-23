# v0.2.5.1：内部验收会话进入“最近”的修补

## 原因与修改

0.2.5 及旧包继承的 App Server 客户端显式使用 `thread/start(ephemeral=false)`，等待回答与重试又会按保存的 thread ID 恢复。上轮真实验收因而留下 `Use $character-… Complete this dispatcher task` 的持久聊天。这个问题出在插件运行器的会话生命周期。

修补在 `creator-src/build.py` 的构建流程维护，并生成到插件运行时：每次内部调用新建临时线程，要求服务返回 `ephemeral:true`，失败时不使用持久化后备；不调用 `thread/resume`。blocked 后从本地 inputs、answers 和 previous_output 重建任务。原设计合同、五阶段资产、批准和已成功产物复用不变。旧 ID 仍可作诊断，不能作恢复凭据。

## 检查结果

- 全量回归 **36 项通过**，其中新增 4 项协议与状态恢复测试。新测试在修补前失败、重建后通过，使用本地协议 stub，不启动模型。
- 真实本机 App Server 生命周期检查调用实际 `AppServer.run` 创建临时线程，并在转发 `turn/start` 前停止：服务确认临时属性、rollout path 为空；关闭前后均不在持久列表；新服务读取返回未加载/不存在；本机线程数据库对应行数为 **0**。本次修补没有启动任何真实模型 turn。
- 已按本地 run 来源与官方当前状态核实并归档 **11 条**历史内部验收聊天；复核“最近”已无这些目标，也未发现其他 dispatcher 标题。归档可恢复，本地运行证据和产物保留。
- ZIP 解压后 doctor 通过：**20 项能力、20 个 Skill**。本机已安装 **0.2.5.1**，135 个 generation-lock 文件与仓库哈希一致。

安装包 `dist/character-assets-0.2.5.1.zip` 包含 136 个文件，SHA-256：`241e595d98412b49efbea47faa1bf9e65406949b8ec4cb056d09b3c99b9cf83e`。详见[机器检查记录](checks.json)和[会话隔离规则](../../character-assets/references/dispatcher-isolation.md)。

协议依据：[OpenAI App Server 文档](https://learn.chatgpt.com/docs/app-server)，并核对本机 CLI 导出的 ThreadStartParams 与 ThreadStartResponse。此次验收覆盖会话隔离与恢复；人物设计能力的真实案例沿用 [v0.2.5 验证](../v0.2.5-validation/README.md)。
