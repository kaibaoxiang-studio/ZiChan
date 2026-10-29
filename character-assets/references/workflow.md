# 正式生产工作流与普通路径边界

普通设计/改稿直接交[同一提示词文档](prompt-document.md)，一个整合方向，四类和多状态按需追加。不前置长稿、typed design、body_form、专项证明或freeze；旧工程可只读继承。明确正式目的、旧scope或typed输入才执行下列生产链，不能把候选版式纠偏扩大为整套工程重启。

## 普通设计与候选词

读取材料／复用有效全文理解 → 人物定位与意图 → 当前相关专项方法形成结构 → 直接形成一个方向的完整提示词 → 一次文字核对 → 保存同一文档。已有成熟稿从核对接续，结构缺哪处补哪处。普通细节主动做；重大身份剧情或已批方向改变集中问。

普通prompt_document自动保存来源、版本和TXT，不写设计JSON或方法台账；下列typed生产记录仅明确正式任务使用。用户明确只对话时仍交完整词，见[提示词合同](prompt-detail-contract.md)。

试改已批人物以正式约束只读、草稿隔离；确认前不submit、不提前使生产失效，采用后再登记真实确认；不自行发动下游审图或重跑。普通候选不需冻结；明确旧typed候选才用冻结接口，错误工程不降独立。

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

生成前仅轻量提示词格式检查，生成后直接交给用户看，默认不自动审图、修补、复核或重跑。明确请求审图才按[审查方法](review.md)实际查看；正式图片由用户人工确认，可走真实人工批准分支，不强制模型先出审图报告，不自称通过。预览/转正保留真实来源、版本与[批准规则](phased-design.md)。

## 打包、变更与历史

当前批准快照机械合成，不新创意；变更只重开实际受影响项。正式包及最终[单元格内图片资产表](final-asset-table.md)保留来源与真实批准。旧complete、各pipeline与旧schema按原合同读，不自动迁移、重算历史批准或整库重画。新规则不倒填旧执行收据。

内部Harness使用[ephemeral隔离](dispatcher-isolation.md)，恢复依赖本地任务与成果，不恢复用户持久聊天。运行器只核结构、来源、依赖和真实交付；模型核人物与语义，用户决定创作选择。不得把测试全绿报告成成图美感通过。
