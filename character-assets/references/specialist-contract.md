# 专项执行、冻结与交付 v0.2.16

方向确定设计意图，专项形成结构与取舍，提示词编译可见结果，生产记录管理来源与批准；四者不能互相冒充。常规由主控真实inline执行，复杂冲突才独立会诊，不要求十三会话或普通首稿先交十三份证明。

## 实际设计工作

先接当前人物理解、任务、世界与动作条件、已选约束和最近比较组，再读相关Skill方法及必要知识，形成形状、比例／落点、连接、表面与状态决定。后台留“本人物问题→所用方法／知识→采用的具体结果→设计位置”。只读资料、复制摘要、职业标签套模板、回填会诊名称都不算执行。区分script_fact／inference／creative_choice，不编身世解释普通骨相。

成熟用户或外部稿按provided/captured记真实来源，结构齐备就接当前复核／编译；缺历史收据不等于缺设计。缺哪个结构只补哪个。独立会诊保留真实返回物，不能把inline伪写independent。专项不自行批准或改写正式记录。

## 本次范围与真实输入

现有task可用 `requested_dimensions:[face,hair,skin,body,costume,adornments]` 表达当前范围；跨维度独立设计的外层仍 `CharacterDesignDeliveryV1`、`kind:standalone,scope:requested`，data仍 `StandaloneCharacterDesignV1` 并含相同requested_dimensions。requested不是新生产scope。现有identity/body/costume与旧complete交付继续兼容，显式生产scope不能被requested降级。

来源绑定实际request与文件哈希；外层仍 `schema_version,kind,scope,data`。独立data保留subject.name/local_key、sources、understanding、design_thesis、payload、实际specialist_execution、deferred_dimensions、unresolved等，按本次维度校验；不造正式CHR ID。真实task传project_root就必须是真工程，不因验证失败改standalone。

`delivery_mode` 默认files；text须本次用户明确只要文字，result.content是实际完整正文，不仅summary；discussion只用于本来讨论请求，不能被执行节点自改以绕过设计交付。文件设计交内部 `design-result.json` 与同源 `design.md`，prompt默认内部JSON／TXT。唯一人用视图见下节。

## 冻结候选与唯一人用文档

已有成熟设计或新稿在ledger外冻结，复用真实CLI，不submit覆盖active：

```sh
python scripts/character_project.py freeze-design --file /internal/design-result.json --inputs /internal/inputs.json --output /internal/frozen
python scripts/verify_design_delivery.py render --design /internal/design-result.json --output /internal/design.md
python scripts/verify_design_delivery.py document --design /internal/design-result.json --prompt /internal/prompt-package.json --output /delivery/角色设计.md
```

freeze-design核真实design和inputs，将冻结文件和来源收据写output，返回 `design_source`：`kind:task_frozen_delivery,path,sha256,inputs_path,inputs_sha256`。prompt使用该实际返回，不能手编SHA或用交付自带task冒充真实inputs。试改可携只读正式project_root及parent_refs，确认采用前不改active、批准或图像有效性。

无工程局部稿编译完整头像时，`freeze-design` 同样用可重复的 `--base-design /internal/既有完整设计.json`，把实际基底path与SHA写进冻结inputs的`base_designs`。读取冻结源会复核基底版本并合并未改脸、身体等结构；不能只冻结hair-only稿就丢掉脸。基底必须同一人物，正式工程试改用真实parent_refs，不能让local base覆盖正式身份。`--markdown`可显式指定所选JSON的内部对应稿；未指定时由所选JSON机械生成校验稿，不误绑同目录另一版design.md。

局部改稿更新已有完整人用文档时，`document` 用可重复的 `--base-design /internal/既有完整设计.json` 继承未改域，再用当前design覆盖实际改动；没有base不允许把旧完整文档覆盖成只剩局部稿。正式stage记录也可作真实base；候选清楚标未替正式。

`render`服务内部固定交付验收；`document`机械更新唯一用户角色设计文档，按人物意图、完整推荐、具体构成、取舍、修改与当前完整prompt组织，不显示工程树。只交设计时可省--prompt。后台JSON/TXT／版本／方法记录不作为用户必用文件。明确text不强制落JSON，也不报告未计算SHA；后续登记保存实际原文和captured_from_conversation来源，不倒填历史会诊／批准。

## 正式阶段继续原合同

正式project的direction、stage与legacy_card返回仍受现有阶段、真实ID、父记录SHA和批准约束；[分阶段](phased-design.md)与[接口](interfaces.md)只在该路线读取。新阶段 `CharacterStageDesignV1.2/execution_contract_version:2` 的inline保留实际knowledge_refs路径／SHA、rules_applied及results映射；independent保留真实proposal_ref/SHA、所选方案与applied_elements。defer激活写任务及原因，不把未做伪装为永远不需。新剧情状态的妆发穿戴按场景任务激活，不改基础身份。

cue来源解析到实际results／applied_elements、实际execution_layout或当前已批父记录；原文事实另保留，不冒充专项成果来源。同物件唯一主责。真实知识快照在正式成功提交时归档，旧记录继续可读，插件升级不因知识哈希变化强迫重做。

独立专项生产提案仍用CharacterSpecialistProposalV1.2，含task、knowledge_refs、facts、options、recommended_option_id、unresolved与不适用理由；实际方案1–3且至少两个可画元素是既有机器合同，不是每个普通聊天再建提案。真实调用该提案时运行 `python scripts/validate_specialist_proposal.py --file /internal/proposal.json`。旧V1/V1.1按原合同回读。

采用试改后才沿已有submit/approve登记，受影响图片按原依赖复核；无变化转录不另加批准仪式，正式本来所需批准仍真实执行。结构、来源和字面一致不证明人物理解、语义或美感，交付前由主控作本次任务复核，有图才作视觉审查。
