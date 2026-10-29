# 正式项目：分阶段、预览与同图转正

图片默认生成后直接交用户人工看，不自动审图/修补/复核/重跑；本页旧审查报告路径仅明确要求时使用。正式批准由用户人工确认，可走真实人工批准分支，保留图像/词/依据哈希和依赖，不先强制模型审图报告，不伪造review pass。人工确认命令见[接口中的人工采用](interfaces.md)，使用--human-reviewed与实际--confirmation-ref，不伪造模型review。


本页只管理明确正式生产及旧typed阶段，不是普通候选词前置。首稿、跨维度人物与局部试改先走[提示词文档](prompt-document.md)，可只读旧工程，不先冻结typed设计或登记本页对象。携project_root本身不等于正式生产。试改确认前不submit覆盖active，也不使生产图提前失效；采用后按下述影响规则复核。普通首稿不被以下工程前置阻塞。

## pipeline_version 3 优先规则

新项目为四图链路：avatar → expression → full_body → execution。身份、身体之后必先由服饰设计师提交并批准 `CostumeStyleBibleV1`，再提交并批准每状态 `stage-design:costume` 文字快照。执行提示词的 design_basis 顺序为 brief、identity、body、costume-bible、当前状态 costume、机械合成 design-card；执行图锚点为获批 avatar/expression/full_body，不再有 `costume_design` 图片或批准门槛。服饰文字设计及图片审查分别批准，图片每状态一次。v2 与 v1 规则见下文，仅旧项目使用。`upgrade-pipeline --project-root PROJECT --operator OPERATOR` 接受未批准服饰/执行图的 v2 项目，保留获批前三类身份图；旧服饰草案失效后重建圣经与文字设计。历史 complete 项目转 phased 后须补齐全文 context、方向、身份与身体快照并经审阅；旧身份图仍绑定迁移时的已批准整卡和原提示词 SHA，不自动改写为新设计依据。


新项目默认 `design_progression:phased`：先理解全剧并确认人物方向，身份阶段看头像，身体与状态服饰按需深化。`init --design-progression complete` 保留先整卡后出图；旧 `project.json` 无此字段按 complete，不自动迁移批准记录。

Harness 的 character-design 对旧 complete 工程保留整卡分支：未给 scope 时默认 complete，也可显式指定 complete；返回 `CharacterDesignDeliveryV1`，`kind:legacy_card`、`scope:complete`，data 为原整卡合同。真实角色、状态、来源哈希和已批全局基准继续检查；新写或修改卡沿现行整卡版本、比例和专项交接门槛，已批准且未改的旧卡保持可读。此分支不自动迁移工程，不批准或改写记录，也不能满足 phased 的 identity/body/costume 阶段任务。未指定创作范围的旧单scope接口保留identity兼容；当前独立跨维度用requested_dimensions，不按默认identity缩小用户请求。

## 1. 可复用的阅读与人物方向

`context-units --project-root PROJECT` 输出覆盖原文的连续阅读块、unit_id、SHA、source_ref和offset；当前块不超过2400字符，JSON也按原文连续读，不拆成海量标量。总控实际阅读全文并综合后提交 `ScriptContextV1`，保存 `source_sha256`、`source_kind:screenplay|biography`、`read_units[{unit_id,sha256}]`、`synopsis`、`world_summary`、`narrative_structure`、`character_index[{character_id,name,role_in_story,arc_summary,relationships,evidence_unit_ids}]` 和 `unresolved`。必须覆盖输出全部单元并匹配哈希，character_index一次轻量覆盖roster全部ID；轻量分析不等于先完成全员人设。覆盖合同不证明语义理解；跨场言行、弧线与信息策略仍按 [总控方法](director-understanding.md) 审阅。

上下文可由项目内其他角色复用，来源变化须补读并更新。只提供小传或片段也能先独立分析，但必须声明范围。正式项目的context完整来源SHA、全部阅读声明与结构且unresolved为空时自动ready，系统记录operator `system:context-contract-check`、scope `source-coverage-and-structure`、`interpretation_confirmed:false`。这只确认阅读声明合同，不额外要求用户批准；未决非空时待复核，手动approve可选。人物解释在design-brief集中确认，visual-bible和cast-plan仍按原流程确认。

随后提交 base 的 `DesignDirectionBriefV1`：`asset_domain:character`、`character_id`、`variant_id:base`、`context_sha256`、`understanding`、`design_thesis`、`visual_strategy:direct|contrast|concealed|mixed`、`recommended_direction`、`alternatives`、`delegated_dimensions`、十三项 `specialist_plan` 和 `unresolved`；inline/independent规划含 `task{objective,character_context,constraints[],expected_result}`。`understanding` 为 `CharacterUnderstandingV1`，包含 `role_in_story`、`core_motivation`、`central_tension`、`world_and_life`、`relationships`、`arc`、`evidence_unit_ids`。字段用于承接人物分析，不是六维问卷；人物理解先于路由。

默认一套推荐，只有重要分歧才填备选。方向确认说明已获授权的意图和委托范围，不能假装完整脸、身体和服饰已经批准。

方向确认后，总控继续在既有委托内执行当前阶段的专项方法并完成可画设计，不再次询问是否深化或是否启用已有 Skill。角色定位、审美关键词和专项计划只是输入，不能代替专项结果；普通细节整合成一套推荐后集中审阅，只有改变人物/剧情或已批方向的选择单独提出。身份阶段不提前完成全身和所有状态，防止重复分析与不必要的审批成本。

## 2. 三类阶段设计快照

`CharacterStageDesignV1` 保存 `character_id`、`variant_id`、`scope`、`parent_refs`、`payload`、`specialist_execution`、`deferred_dimensions`、`unresolved`。`parent_refs` 用实际记录键映射当前 SHA；采用 [专项执行合同](specialist-contract.md) 的 inline/independent 结果，未深化部分放 deferred，不写成无需求。从defer激活补 work.task和activation_reason；改变执行方式记execution_change_reason，基础身份的 not_needed 不跨状态继承；新身份与服饰状态使用 `CharacterStageDesignV1.2`，旧 V1/V1.1 保持可读；新提示词另按 [提示词保真合同](prompt-detail-contract.md) 逐项核对当前可见结构与 [剧情状态可见需求](scene-styling-needs.md)，可凭具体任务及 `state_activation_reason` 激活妆、发、头耳颈或其他穿戴专项。旧 V1 保持可读，其余领域 not_needed 改为执行仍须先改方向稿。

新建或本轮重做的 `CharacterStageDesignV1.2` 增加 `execution_contract_version:2`。当前阶段须有实际专项成果，而不只是填满 `prompt_detail_contract`：每个可见设计 cue 应能解析到已采用的专项结果，布局和已批父记录继承按 [专项合同](specialist-contract.md) 的明确例外处理。事实依据保存在原文/推导字段，不能把任意原文引用当成专项已完成的证明。已有批准记录仍按原合同回读，不自动改写或失效；新设计不能通过改用旧 schema/省略标记来降级。

| scope | 所属状态 | payload 的当前阶段设计 |
| --- | --- | --- |
| `identity` | base | `morphology`、`appearance`、`feature_focus`、`world_influences`、`facial_surface`、`differentiation_review`、`identity_invariants`；`visual_details.face/hair/skin/adornments.head_neck` |
| `body` | base | `visual_details.body` 与完整 `body_form`，含可核对比例、体块和行动检查 |
| `costume` | 当前资产表状态；无状态则base | `costume` 摘要，`visual_details.costume/adornments.body_hands`，该状态衣装、鞋履、饰物与获批妆面 |

非人新phased可用 `payload.morphology_details` 的 identity/body/costume 分域写当前形态具象描述，`visual_details`可空；不强制人脸、毛发、衣装或人类比例，身份、世界、焦点和证据合同仍保留。

各阶段可增加 `facts`、`inferences`、`approved_choices` 与适用的 `recognition_axes`；facts每项source_refs、inferences每项basis_refs当阶段就须非空，不拖到合成才补；同一身份字段不能相互冲突。identity 不要求提前完成腿部比例或服饰缝线，body 不得重新设计已批准面孔。首图中普通痣雀斑可与身份快照整体确认；新增经历含义的特征须显式决定。阶段world_influences/facial_surface可用inference或creative_choice保留来源性质；最终V2.5仍保留该来源标签，是否获批由外层approval和SHA决定，不把创意改写成script_fact或假称已批。

提交命令示意如下；`approve-record` 只在用户已确认对应内容后执行：

```sh
python scripts/character_project.py context-units --project-root /work/role-project
python scripts/character_project.py submit --project-root /work/role-project --kind script-context --file /draft/context.json
python scripts/character_project.py submit --project-root /work/role-project --kind design-brief --character-id CHR-001 --variant-id base --file /draft/direction.json
python scripts/character_project.py approve-record --project-root /work/role-project --kind design-brief --character-id CHR-001 --variant-id base --operator OPERATOR
python scripts/character_project.py submit --project-root /work/role-project --kind stage-design --scope identity --character-id CHR-001 --variant-id base --file /draft/identity.json
```

阶段metadata与可见字段同样守分域：identity_invariants只属identity；approved_choices.field须指向当前payload实际存在的本域字段；recognition_axes中face_structure/hair_structure属identity，silhouette/body_posture属body，costume_color属costume。morphology_details只含当前scope。body/costume若追加world_influences，只能写appearance_effects数组，各项除feature/mechanism/basis/evidence_status外须有field，指向本域实际可见字段；不得重设environment/technology/resources_and_access或改写身份世界规则。

独立首稿中的类型标称不是生产项目合同：人物理解可能只是可读摘要；正式 submit 时须补齐完整对象、十三项对象式 specialist_plan 和准确 parent_refs。经 Harness 返回的独立成果仍须符合 `CharacterDesignDeliveryV1` 的 standalone 分支，有真实来源和当前阶段的专项成果，但不强制创建项目或全员记录。参照 [专项交接](specialist-contract.md) 与 [最小身份合同样例](../examples/phased-identity-contract.md)，不要把独立草案原封不动提交。

## 3. 正式设计依据（下表为 v2；v3 见顶部优先规则）

phased 的 `CharacterPromptPackageV1` 使用 `design_basis:{records:{记录键:sha}}`，省略 `design_card_sha256`。各阶段最低依据：

| 图像阶段 | 必须在 records 中出现的当前记录 |
| --- | --- |
| avatar、expression | `design-brief:CHR:base`、`stage-design:identity:CHR:base` |
| full_body | 上述两项，加 `stage-design:body:CHR:base` |
| costume_design | 上述三项，加 `stage-design:costume:CHR:STATE` |
| execution | 上述四项，加 `design-card:CHR:STATE` |

将 CHR、STATE 替换为真实角色与状态 ID。正式提示词的全部依据必须已批准且哈希匹配。图片的 `anchor_images` 按项目 pipeline_version 绑定正式上游图：v3 四图，v2 五阶段；设计快照不代替图片锚点。complete 模式继续用批准整卡的 `design_card_sha256`，头像保持既有 2–3 条候选；phased 允许 1–3 条，默认一套推荐。

## 4. 头像 preview 与原图转正

默认先确认方向，再让身份草案以头像快看：提示词 `purpose:preview`、`preview_mode:direction_first`，brief 已批准，identity 可以未批准但已提交冻结；两者 SHA 放入 `design_basis.records`。只有用户明确要求先图后确认方向时才用 `preview_mode:image_first`，此时 brief 和 identity 都可未批准，但仍已提交冻结；script-context须ready，visual-bible与cast-plan仍须先批准。

预览与正式身份设计使用相同的专项深化和可追溯颗粒度；只允许上述批准时点差异。不因“候选”“文字版”“批量先铺一轮”而跳过专项或把方向摘要拼为短词。冻结草案与已批准草案均须能回答具体设计来自哪项实际成果；模板只负责序列化与导出。

preview 只用于看方向和首稿，不是正式身份锚点，不能推进九宫格、打包或用回图意外细节悄悄改卡。图片生成后直接展示；明确要求正式登记时导入，人工确认可直接采用，不默认启动模型审查。希望采用首图时：

1. 对照该图冻结的 brief 和 identity 审阅方向、人物细节与普通标记，清空 unresolved；如修改了快照内容，原 SHA 不再匹配，不能直接转正原图。
2. 采用人工确认分支时不要求模型review pass；采用显式模型审查分支时其结果须真实。两分支均保持图文件、提示词及依据SHA不变。
3. 用户确认设计和该图后，执行 `promote-candidate --image-id ID --operator OPERATOR`；原依据须先批准。若用户一次明确确认同一份方向/身份和该图，可加 `--approve-design-basis`，显式批准同 SHA 依据并转正同一图片。

```sh
python scripts/character_project.py promote-candidate --project-root /work/role-project --image-id avatar-HASH --operator OPERATOR --human-reviewed --confirmation-ref '实际用户确认定位' --approve-design-basis
```

这是有明确确认与哈希约束的同图转正，不要求重新生图，也不自动接受未审的其他候选。缺真实人工确认、依据/图像变更或未决硬冲突时不得转正；显式使用模型审查分支时保留其实际结论，不能伪造pass。需要修改设计时保留旧预览，提交新版本；生成图直接交用户，审图/修改/重跑仅按明确请求执行。

## 5. 后续深化、合成与兼容

头像正式后制作九宫格；身体快照确认后制作9:16全身模卡；v3 每状态服饰快照确认后直接准备 9:16 四格 execution 图；v2 才另制作服饰图。execution 前运行：

```sh
python scripts/character_project.py compile-design-card --project-root /work/role-project --character-id CHR-001 --variant-id STATE_ID
```

合成使用 base identity、base body 和当前状态 costume，输出 `CharacterDesignCardV2.5`；无状态用 base costume。只机械合并同 SHA 已批准的阶段设计，不生成新创意，冲突则阻断；审批以 `system:approved-scope-composition` 和 `inherited_from` 继承源快照的实际批准记录，不重复要求用户确认同一套细节。不能直接 submit 手写 V2.5 卡；新增设计必须回阶段快照。合成卡用于 execution 和正式打包，保留来源和哈希，供后续跨资产读取。

已批准旧卡、旧四阶段和 complete 流程继续回读。新增人物理解可作为待审改进，不自动推翻既有设计；旧项目需要切换深化方式时先明确迁移范围，不擅自重置批准。
