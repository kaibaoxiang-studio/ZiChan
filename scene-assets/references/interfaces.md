# 场景插件接口 v0.1

JSON 文件使用 UTF-8，关键记录含 `schema_version`。场景 ID 使用上游资产表的稳定 ID；文件来源以 `{path,sha256}` 保存，事实以 `source_refs` 指向原文位置。若上游已有带批准记录的 `ProjectVisualBibleV1`，读取并核对其哈希与操作者审批。

- `ProjectVisualBibleV1`：`project_id`、`world_rules[]`、`style{fantasy_scale_enabled:boolean}`、`evidence[]`、`unresolved[]`。把来源观察事实与批准的创作选择分开。
- `SceneDesignCardV1`：`scene_id`、`variant_id`、`visual_bible_sha256`、`facts[{text,source_refs}]`、`approved_choices[]`、`primary_space{}`、`scale_cues[]`、`composition{}`、`continuity_invariants[]`、`source_refs[]`、`unresolved[]`、`fantasy_scale_enabled`。为真时须能追溯到已批准视觉基准或单场批准记录。
- `ScenePromptPackageV1`：`scene_id`、`variant_id`、`design_card_sha256`、`target_model`、`reference_images[]`、`prompts[{id,text}]`、非空 `acceptance_checks[]`。提示词只给外部操作者，不内置生图调用。
- `SceneImageReviewV1`：`image_sha256`、`verdict`、`factual_conflicts[]`、`continuity_issues[]`、`space_scale_issues[]`、`layout_issues[]`、`blocking_issues[]`、`adoption_proposals[]`。`pass` 时全部缺陷数组为空。
- `SceneAssetPackV1`：已批准视觉基准、场景设计卡、提示词、实际选定的图、审查与操作者审批、上游文件 SHA、插件来源收据。

主流程：输入版本 → 视觉基准批准 → 场景设计卡批准 → 提示词 → 外部出图 → 实图审查 → 操作者批准 → 打包。首版输入更新时保守撤销全部旧审批，要求重新核对并提交；不静默沿用，也不声称已完成场景级影响分析。
