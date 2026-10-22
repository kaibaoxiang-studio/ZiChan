# 角色专项设计的共同交接

专项 Skill 可单独调用，也可由 `$character-assets` 或 `$character-design` 在相应缺口出现时使用。它不自行改变项目批准状态。

## 输入

读取当前标准剧本证据、资产表角色 ID、已批准视觉基准、全员轻规划、目标角色的已批准设计和最近比较组。缺少项目时接受用户提供的角色简介作独立设计，但将没有证据的内容标为提案，不伪称剧本事实。只读取本专项知识快照和必要的共同参考。

## 输出

在本次调用允许的 `artifact_dir` 写一份 `CharacterSpecialistProposalV1` JSON 和供人审阅的简短 Markdown；主控收到后可复制到项目 `drafts/`。JSON 至少包含 `schema_version`、`specialist`、`character_id`、`scope`、`facts[{text,source_refs}]`、`options[{id,visible_design,rationale,comparison_difference,production_check}]`、`recommended_option_id`、`unresolved[]`、`not_applicable_reason`。一般给 2–3 套真正不同的方向；若事实只允许一套，加 `single_option_reason`；专项不适用时说明 `not_applicable_reason` 且不交设计选项。未获得操作者选择时，`recommended_option_id` 只是建议，不能写入 `approved_choices`。

交接前执行 `python scripts/validate_specialist_proposal.py --file /absolute/artifact_dir/proposal.json`；脚本检查必填、事实来源、选项数量、比较与制作核对字段。它只验证结构，方案质量仍由主控与操作者判断。

群像总控的审查报告单独写在允许的 `artifact_dir`，使用 `CharacterCastDifferentiationReviewV1`：标明文本或实图证据等级、比较组及来源、五轴矩阵、具体混淆点、真实度疑点、尚未做的视觉检查和未实施建议。报告是复核材料，不修改项目批准状态。

## 判定原则

每套方案写能出图的结构、连接方式、层次、磨损或尺度，而不是“好看、有气质”。解释其剧本/世界依据和与近邻角色的差异。演员或影片参考只抽取用户指明的审美方向，生成原创身份；不要把真人肖像当默认模板。若两个专项发生冲突，交给主控平衡焦点并保持已批准身份不变量。

“无饰品”“无特殊皮肤痕迹”“服饰简洁”等可以是有意识的设计，不因必须制造记忆点而强加物件。非人形角色按可见形态适用；不把人类发型、五官或服装硬套到非人。专项本身不要求用户确认每一个微小参数；主控把相关待选项合并到一轮审阅。
