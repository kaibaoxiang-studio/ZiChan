# 接口与文件契约 v0.1

所有文件为 UTF-8 JSON。每份产物含 `schema_version`，用资产表的稳定 `CHR-...` 角色 ID。`source_refs` 引用标准剧本位置；若上游只提供 Markdown/Excel，使用导入后保留的 `文件名:L行号` 或 `文件名:工作表!R行号`。键值的具体描述可扩充，下面的必填字段及含义不能改。

## 顶层兼容输入

角色插件可直接接收三份文件，也可用 `init --snapshot` 读取 `AssetProjectSnapshotV1`。快照至少包含 `project_id`、`sources.screenplay` 与 `sources.asset_table` 的 `{path,sha256}`；`sources.scene_log` 可选。`visual_bible` 可选，但存在时须是 `{path,sha256,approval:{operator,at,sha256}}`。相对路径相对于快照文件所在目录。接入时校验文件 SHA 与批准状态，再映射为本插件状态；不能只靠同名文件猜测版本。

## ProjectVisualBibleV1

`project_id`、`world_rules`（世界规则及其可见后果）、`style`（媒介、写实度、时代、色彩、材质、光线等已确认维度）、`evidence[{claim,source_refs}]`、`unresolved[]`。风格项注明原文约束或获准创作选择；全剧共用，不覆盖个别角色的特殊事实。

## CastPlanV1 / CastPlanV2

`characters[]` 必须覆盖资产表每个角色 ID，各项至少有 `id`、`design_distinction`，推荐附 `tier`、`narrative_role`、`relationships`、`visual_anchor`、`candidate_variants`、`source_refs`；另有 `unresolved[]`。轻规划不需要填每人的完整脸型。

0.2.0 新轻规划使用 `CastPlanV2`。每行加 `recognition_axes`，含 `silhouette`、`face_structure`、`body_posture`、`hair_structure`、`costume_color` 五个非空字符串；轻规划时未知可写“待定”。非人或群像行还应写 `morphology: nonhuman|group`，不适用的轴可写“不适用：原因”，审查脚本会单列而不算缺失。每个轴写可见结构而非“美丽/英俊/特别”。旧项目的已批准 `CastPlanV1` 保持可读，不因升级自动作废。

## CharacterDesignCardV1 / V2 / V2.1 / V2.2 / V2.4

必填 `character_id`、`variant_id`、`morphology`（`human|humanoid|nonhuman`）、`facts[{text,source_refs}]`、`inferences[{text,basis_refs}]`、`approved_choices[{field,value,rationale}]`、`identity_invariants[]`、`appearance{}`、`costume{}`、`unresolved[]`。可加 `reference_extracts`、`variant_of`、`execution_layout`、`forbidden_changes`。事实一定有来源；推导不能伪装成事实。变体沿用同一个角色 ID，并注明与基础造型的变化范围。

0.2.0 新设计卡使用 `CharacterDesignCardV2`，额外包含同样五轴的 `recognition_axes` 和 `differentiation_review{closest_character_ids[],shared_features[],distinct_features[],realism_check}`。`distinct_features` 应写实在可见的对照结果，而非“更漂亮”。无可比角色时 `closest_character_ids` 可空并说明依据。旧 `CharacterDesignCardV1` 仍可读取和打包；只在用户请求修改时按原审批流程升级。

0.2.1 起新提交的重点人形卡使用 `CharacterDesignCardV2.1`，继承 V2 字段，并要求 `visual_details` 六组 18 个具象字段：`face{contour,brow_eyes,nose_mouth}`、`hair{hairline_part,volume_flow,length_texture_color}`、`body{frame_proportions,weight_posture}`、`skin{tone_variation,surface_distribution}`、`costume{silhouette_layers,neckline,shoulder_sleeve,seams_fastening_mobility,material_drape_wear,color_placement}`、`adornments{head_neck,body_hands}`。另有 `specialist_coverage`，10 个专项 ID 各填 `{status:used|not_needed,decision,proposal_ref?,applied_fields?}`，used 时 `proposal_ref` 与指向 `visual_details` 的非空 `applied_fields[]` 必填。文本应写形状、位置/比例、连接或材料行为，不用“结构清楚、自然垂落”作唯一设计。具体方法和示意见[具象描述标准](design-detail-standard.md)。既有 V1/V2 卡继续可读、已有批准保持有效；重点人形卡重新提交时须升级到 V2.1。非人仍可用 V2，并按形态提供对应的可见结构。

新专项提案是 `CharacterSpecialistProposalV1.1`，每选项增加至少两条 `design_elements[{part,visible_feature,placement_or_structure,basis}]`；旧 V1 可回读。格式见 [专项交接](specialist-contract.md)，属于草案，不自动写进设计卡。全员差异化文本审查用 `CastDifferentiationAuditV1`，不代替看图；运行 `python scripts/cast_diff_audit.py --project-root PROJECT --output PROJECT/drafts/cast-differentiation-audit.json`，或用 `--cast-plan FILE` 审查未提交草案。

0.2.2 起新提交的重点人形卡使用 `CharacterDesignCardV2.2`。除六组细节外，新增 `feature_focus`、`body_form`、`route_ref`、`route_sha256`，并覆盖 11 个专项。used 项另需 `proposal_sha256`、`selected_option_id`、`applied_elements[{field,element_index}]`；提案必须是目标角色与专项的 V1.1 原样 JSON，文件放项目 `drafts/specialists/`。路由须是同一角色/变体的 `CharacterSpecialistRouteV1`，invoke/skip 与 used/not_needed 一一对应。提交、批准及后续读取时校验哈希。旧已批准卡仍可读；重新提交重点人形卡用 V2.2。详见[焦点与三维形体交接](feature-focus-and-body-form.md)。

0.2.3 不改卡的 `schema_version`；新提交的人形 V2.2 卡增加 `body_form.proportion_anchors`。其中 `measurement_frame` 写测量姿态与端点，`head_body`、`shoulder_hip`、`torso_legs`、`arm_segments`、`leg_segments` 各为 `{mode:"numeric"|"landmark",reference_points:[至少两个],relation,basis}`。`head_body` 必须是明确的头高与全高数值比；其他项可用数值或具体骨点相对位置。`relation` 必须逐字包含列出的 `reference_points`，并同步进入设计卡身体摘要；全身提示词须继承已批准的头身、肩胯与躯腿关系，验收项须核对头身与躯腿。原有已批准 V2.2 卡仍可读取和打包，但缺这些锚点的卡不得新提交全身提示词；先经操作者确认比例并更新设计卡。示例见[身体比例交接样例](../examples/body-proportion-contract.md)。

0.2.4.1 新项目的重点人形卡使用 `CharacterDesignCardV2.4`，延续 V2.2 的具象与比例合同，路由覆盖 13 项。新增 `world_influences:{environment,technology,resources_and_access,appearance_effects:[{feature,mechanism,basis,evidence_status}]}`，以及 `facial_surface:{stable_marks:[],applied_decoration:[],temporary_effects:[],absence_or_focus_decision}`。面部数组非空项必有 `feature,placement,visible_form,narrative_basis,continuity,evidence_status`。`evidence_status` 只能是 `script_fact` 或 `approved_choice`；未批准的创意只留在提案，不写入正式卡。空数组可表示有依据的无妆/无标记决定。旧批准卡继续有效。

## CharacterPromptPackageV1

必填 `stage`（`avatar|expression|full_body|costume_design|execution`）、`target_model`（GPT Image 2.5）、`character_id`、`variant_id`、`design_card_sha256`、`anchor_images{}`、`reference_images[]`、`prompts[{id,text}]`、非空 `acceptance_checks[]`。新项目的 `avatar`、`expression`、`full_body` 用 `base` 卡；`costume_design` 与 `execution` 用当前资产表状态卡。新项目阶段锚点依次为：头像空；九宫格含头像；全身含头像和九宫格；状态服饰图含三张基础图；执行图再含本状态服饰图。头像有同设计 2–3 条；表情默认 `labels[]` 长度 9 且每项有中文，16 格仅在 `grid_explicit_user_override:true` 与 `grid_override_basis` 记录用户明确选择时使用；单独全身图加 `head_visible:true` 与 `feet_visible:true`；服饰图加与资产表一致的 `variant_name`，验收项须核对服饰结构；人形执行表加：

```json
"layout": {
  "top_left": "front_face",
  "top_right": "three_quarter_face_45",
  "bottom_left": "headless_enlarged_front_costume",
  "bottom_right": "complete_back_head_to_shoes"
}
```

非人执行表在设计卡中批准替代布局，提示词包的 `layout` 必须与设计卡一致。包内设计卡与锚点图片哈希必须匹配当前批准版本，防止误用旧版身份锚点。

头像和全身提示词包都必须有 `aspect_ratio`：头像默认 `"3:4"`，全身默认 `"9:16"`。每条 `prompts[].text` 都要写出对应比例；全身 `acceptance_checks[]` 还须核对 9:16。仅当操作者明确要求其他比例时，填写新比例、`aspect_ratio_explicit_user_override:true` 和 `aspect_ratio_basis`（记录具体用户决定）。现有批准的旧包不会因缺新字段而自动失效。

新提交的人形头像、表情与单独全身提示词包还必须有 `reference_attire`，按[模卡规则](model-card-baseline.md)选择：头像/表情为 `face_only`（服装不入画，取景不限制在锁骨以上）、`white_tank` 或 `white_sports_tank`（上胸入画时可直接选用）；全身为 `white_tank_shorts_barefoot` 或 `white_sports_tank_black_shorts_barefoot`。从已批准的 `face_only` 头像切换到背心表情时填写 `reference_attire_basis`；不适用模卡方案时用 `approved_exception`，同时填写 `reference_attire_basis` 和 `reference_attire_description`。每条提示词及验收项均须写明对应可见着装。全身图的模卡服装不是剧情换装；执行资产表恢复设计卡中获批准的正式服装、鞋履与饰物。旧已批准包仍保持可读。

## CharacterImageReviewV1 与 CharacterAssetPackV1/V2

审查报告必填 `image_sha256`、`stage`、`verdict`（`pass|revise|uncertain`），及数组 `factual_conflicts`、`identity_issues`、`layout_issues`、`label_issues`、`blocking_issues`、`adoption_proposals`。`pass` 时缺陷数组都应为空；视觉判断必须基于实际收到的图片。

打包包含 `manifest.json`、已批准设计/提示词/图片/审查报告及插件来源收据。清单列每个文件 SHA、插件版本、上游来源版本、图片用途和审批记录。打包时重新计算输入、记录、图片、审查和参考图的哈希；任何内容与批准版本不符即停止。新项目使用 `CharacterAssetPackV2`：base 三张身份图与当前状态的服饰、执行图均须审查通过且由操作者批准；旧项目继续按 `CharacterAssetPackV1` 四阶段打包。新图片文件名以角色资产名和状态名开头，后接阶段名与短 SHA，确保可读且避免同名覆盖。
