# 角色资产项目工作流

插件主入口是 `$character-assets`。先读 `knowledge/index.md`，只加载本阶段的规则。所有创作内容由 Codex Skill 编写；`scripts/character_project.py` 负责文件、版本、批准与发布门槛。不要把 CLI 的合同通过冒充为视觉审查通过。

## 1. 建项目并检查来源

操作者可以在聊天上传文件，也可以给本地路径。将可访问的附件路径交给 CLI；项目工作目录由操作者指定，不放入插件目录。标准剧本和资产表必填，场记可选。

```sh
python scripts/character_project.py init --project-root /work/role-project --project-id PROJECT_ID --screenplay /input/standardized_screenplay.json --asset-table /input/assets.json --scene-log /input/scene_log.json
python scripts/character_project.py status --project-root /work/role-project
```

如果没有场记，省略 `--scene-log` 并在表情/镜头需求中注明少了一条校对来源。CLI 复制原件并记录 SHA；JSON 优先，Markdown 次之，Excel 最后。不要把仅供浏览的 Excel 当作比原文更高优先级的证据。

若顶层插件已生成 `AssetProjectSnapshotV1`，改用 `init --project-root /work/role-project --snapshot /input/asset-project-snapshot.json`。CLI 核对来源文件哈希；快照里如有已批准视觉基准，也同步导入其批准记录。详见 [接口](interfaces.md)。

## 2. 项目与角色决策

从三份输入形成 `ProjectVisualBibleV1`，人工确认；再由 `$character-cast-differentiation` 建比较组与五轴矩阵，形成覆盖资产表角色 ID 的 `CastPlanV2`，人工确认。重点角色按分轮 Grill Me 生成 `CharacterDesignCardV2`，人工确认。旧项目的 V1 批准记录继续有效。草案可以列 `unresolved`，但不能批准。使用 `submit` 保存 JSON，再用 `approve-record --operator 操作者姓名` 确认。设计卡变更会让该角色的后续提示词与图片失效，历史文件保留。

在轻规划草案提交前及每张重点角色设计卡定稿前，按 [差异化框架](differentiation-framework.md) 检查最相近角色。只有发型、体型、面孔、皮肤或服饰存在实际缺口时调用相应专项；专项提案先并入当前审阅轮，不为每个维度单开确认。可用 `python scripts/cast_diff_audit.py --cast-plan /draft/cast-plan.json --output /draft/cast-audit.json` 找出同字段和缺轴候选；人仍需审查近义撞型与全员美型。已有已批准角色不会因插件升级自动被改写。

```sh
python scripts/character_project.py submit --project-root /work/role-project --kind visual-bible --file /draft/visual-bible.json
python scripts/character_project.py approve-record --project-root /work/role-project --kind visual-bible --operator OPERATOR
python scripts/character_project.py submit --project-root /work/role-project --kind cast-plan --file /draft/cast-plan.json
python scripts/character_project.py approve-record --project-root /work/role-project --kind cast-plan --operator OPERATOR
python scripts/character_project.py submit --project-root /work/role-project --kind design-card --character-id CHR-001 --variant-id base --file /draft/card.json
python scripts/character_project.py approve-record --project-root /work/role-project --kind design-card --character-id CHR-001 --variant-id base --operator OPERATOR
```

参考图先通过 `import-reference --role identity|costume|style|inspiration --desired-strength '具体提取点'` 登记。`desired-strength` 写要吸收的可见优点；操作者确认后才进入设计卡。个人参考图可以加 `--character-id`。

## 3. 提示词与图片回流

每阶段由 `$character-image-prompt` 编写 `CharacterPromptPackageV1`，经 `submit --kind prompt-package --stage ...` 合同检查后可用于外部出图。顺序为头像 → 表情与全身并行 → 执行资产表。每阶段图片用 `import-image` 登记，再由 `$character-image-review` 实际看图、保存 `CharacterImageReviewV1`。报告通过后，操作者用 `approve-image` 选定唯一当前版本。只报“通过”而不见图、未经操作者确认，都不能推进。

头像与全身图回流审查时，若已有同剧定稿图片，增加并排比较：脸型、发结构、体态和皮肤是否在成图里保持区别；无法取得其他角色图片时写明只做单人核验。差异问题先定位设计卡还是出图偏差，修设计卡须重走批准，单纯出图偏差可走局部修图。

```sh
python scripts/character_project.py submit --project-root /work/role-project --kind prompt-package --character-id CHR-001 --variant-id base --stage avatar --file /draft/avatar-prompt.json
python scripts/character_project.py import-image --project-root /work/role-project --character-id CHR-001 --variant-id base --stage avatar --path /images/avatar-1.png
python scripts/character_project.py submit-review --project-root /work/role-project --image-id avatar-HASH --file /draft/avatar-review.json
python scripts/character_project.py approve-image --project-root /work/role-project --image-id avatar-HASH --operator OPERATOR
```

`$character-image-edit` 读取缺陷报告，输出目标明确的局部修图提示词；修改图重新导入、审查、确认。表情和全身均定稿后，才提交执行资产表提示词。最终 `package --character-id ... --output NEW_DIRECTORY` 汇总四阶段定稿图片、设计与提示词、审查和版本记录。输出目录必须是新目录，避免覆盖旧包。

## 4. 剧本侧改版

`refresh` 只导入确有变化的来源。资产表角色记录变化会自动让相关角色设计和下游失效；剧本或场记变化需给出影响分析。处于 `pending_impact` 时禁止新设计决策和发布。检查变化后执行 `resolve-impact --affected CHR-001 CHR-002 --operator OPERATOR`；若改变全剧画风/世界规则，另加 `--global-style`。不可断言“无影响”而不检查新旧内容。未受影响角色仍保留原批准版本。

CLI 是本地状态管理器，不负责发图、读懂画面或自动给历史文化结论；这些由技能和操作者处理。
