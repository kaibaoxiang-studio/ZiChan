# 接口与文件契约 v0.1

所有文件为 UTF-8 JSON。每份产物含 `schema_version`，用资产表的稳定 `CHR-...` 角色 ID。`source_refs` 引用标准剧本位置；若上游只提供 Markdown/Excel，使用导入后保留的 `文件名:L行号` 或 `文件名:工作表!R行号`。键值的具体描述可扩充，下面的必填字段及含义不能改。

## 顶层兼容输入

角色插件可直接接收三份文件，也可用 `init --snapshot` 读取 `AssetProjectSnapshotV1`。快照至少包含 `project_id`、`sources.screenplay` 与 `sources.asset_table` 的 `{path,sha256}`；`sources.scene_log` 可选。`visual_bible` 可选，但存在时须是 `{path,sha256,approval:{operator,at,sha256}}`。相对路径相对于快照文件所在目录。接入时校验文件 SHA 与批准状态，再映射为本插件状态；不能只靠同名文件猜测版本。

## ProjectVisualBibleV1

`project_id`、`world_rules`（世界规则及其可见后果）、`style`（媒介、写实度、时代、色彩、材质、光线等已确认维度）、`evidence[{claim,source_refs}]`、`unresolved[]`。风格项注明原文约束或获准创作选择；全剧共用，不覆盖个别角色的特殊事实。

## CastPlanV1

`characters[]` 必须覆盖资产表每个角色 ID，各项至少有 `id`、`design_distinction`，推荐附 `tier`、`narrative_role`、`relationships`、`visual_anchor`、`candidate_variants`、`source_refs`；另有 `unresolved[]`。轻规划不需要填每人的完整脸型。

## CharacterDesignCardV1

必填 `character_id`、`variant_id`、`morphology`（`human|humanoid|nonhuman`）、`facts[{text,source_refs}]`、`inferences[{text,basis_refs}]`、`approved_choices[{field,value,rationale}]`、`identity_invariants[]`、`appearance{}`、`costume{}`、`unresolved[]`。可加 `reference_extracts`、`variant_of`、`execution_layout`、`forbidden_changes`。事实一定有来源；推导不能伪装成事实。变体沿用同一个角色 ID，并注明与基础造型的变化范围。

## CharacterPromptPackageV1

必填 `stage`（`avatar|expression|full_body|execution`）、`target_model`（GPT Image 2.5）、`character_id`、`variant_id`、`design_card_sha256`、`anchor_images{}`、`reference_images[]`、`prompts[{id,text}]`、非空 `acceptance_checks[]`。`anchor_images` 在头像阶段是空对象；表情/全身阶段含 `avatar` 的已批准图 SHA；执行阶段再含 `expression` 与 `full_body` 的已批准图 SHA。头像有同设计 2–3 条；表情加 `labels[]`，长度 9 或 16，且每项有中文；单独全身图加 `head_visible:true` 与 `feet_visible:true`；人形执行表加：

```json
"layout": {
  "top_left": "front_face",
  "top_right": "three_quarter_face_45",
  "bottom_left": "headless_enlarged_front_costume",
  "bottom_right": "complete_back_head_to_shoes"
}
```

非人执行表在设计卡中批准替代布局，提示词包的 `layout` 必须与设计卡一致。包内设计卡与锚点图片哈希必须匹配当前批准版本，防止误用旧版身份锚点。

## CharacterImageReviewV1 与 CharacterAssetPackV1

审查报告必填 `image_sha256`、`stage`、`verdict`（`pass|revise|uncertain`），及数组 `factual_conflicts`、`identity_issues`、`layout_issues`、`label_issues`、`blocking_issues`、`adoption_proposals`。`pass` 时缺陷数组都应为空；视觉判断必须基于实际收到的图片。

发布包含 `manifest.json`、已批准设计/提示词/图片/审查报告及插件来源收据。清单列每个文件 SHA、插件版本、上游来源版本、图片用途和审批记录。打包时重新计算输入、记录、图片、审查和参考图的哈希；任何内容与批准版本不符即停止。只有头像、表情、全身、执行四阶段均有审查通过且由操作者批准，才能发布该角色变体。
