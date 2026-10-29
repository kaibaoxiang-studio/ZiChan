# 角色设计与生产工作流 v0.2.16

默认从本次成果开始，不强先建生产工程。先读[路由](routing-and-integration.md)，新创作按[人物方法](director-understanding.md)实际设计；文件与冻结接口见[专项交付](specialist-contract.md)。

## 普通设计与候选词

读取材料／复用有效全文理解 → 人物定位与意图 → 当前相关专项方法形成结构 → 总控整合和一次任务复核 → 完整可读设计 → 按需编译候选词。已有成熟稿从核对接续，结构缺哪处补哪处。普通细节主动做；重大身份剧情或已批方向改变集中问。

后台按真实task存设计JSON、输入、最小方法成果；提示词默认JSON和机械TXT。唯一人用文档由同一设计和当前prompt机械更新，图片单独；不让用户管理内部文件。用户明确只对话时可完整文本交付，不先落JSON。详见[提示词合同](prompt-detail-contract.md)。

试改已批人物以正式约束只读、草稿隔离；确认前不submit、不提前使生产失效，采用后再登记并复核相关图片。没有工程可独立冻结，错误工程不能自动当无工程。

## 进入正式项目

正式项目需要标准剧本与资产表，场记可选；使用内置真实命令初始化，不写插件源码目录：

```sh
python scripts/character_project.py init --project-root /work/role-project --project-id PROJECT --screenplay /input/screenplay.json --asset-table /input/assets.json --design-progression phased
python scripts/character_project.py context-units --project-root /work/role-project
python scripts/character_project.py plan --project-root /work/role-project --character-id CHR-001 --stage avatar
```

context覆盖与来源完整且unresolved为空可自动ready，interpretation_confirmed:false，不新增用户审批。视觉基准和全员轻比较按正式依赖建立；不是先做全员详设。方向及当前阶段按用户实际确认批准。实际命令和字段见[阶段合同](phased-design.md)及[接口](interfaces.md)。普通成熟稿登记是忠实转录与映射，不重做人设，不倒填历史会诊／批准。无变化转录不另审批，正式阶段本来需要的批准仍保留。

## 正式资产链

新pipeline 3常规人物：身份设计→头像3:4→九宫格→身体设计与9:16模卡→服饰圣经→逐状态服饰文字快照→机械合成卡→每状态一张9:16人形四格执行图。非人用获批替代布局。模卡中性背心短裤赤脚不成为剧情服装。

有台词群演每状态一张9:16执行图，人形四格、非人给定形态布局；无台词群像每状态一张完整全身同画布图，明确人数照数，横向比例按辨识选择。两者跳过前三身份图与穿衣圣经。见[群演规则](group-ensemble.md)。

所有实际图片须打开审查；身份、体型、衣装、状态、标签、比例、格位、裁切、背景核对后，用户确认才作正式锚点。候选不自动获批，不以工具返回代替看图。预览与同图转正沿已有[批准规则](phased-design.md)。

## 打包、变更与历史

当前批准快照机械合成，不新创意；变更只重开实际受影响项。正式包及最终[单元格内图片资产表](final-asset-table.md)保留来源与真实批准。旧complete、各pipeline与旧schema按原合同读，不自动迁移、重算历史批准或整库重画。新规则不倒填旧执行收据。

内部Harness使用[ephemeral隔离](dispatcher-isolation.md)，恢复依赖本地任务与成果，不恢复用户持久聊天。运行器只核结构、来源、依赖和真实交付；模型核人物与语义，用户决定创作选择。不得把测试全绿报告成成图美感通过。
