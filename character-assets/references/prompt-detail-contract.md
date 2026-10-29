# 提示词与设计保真 v0.2.17

普通路径提示词就是设计稿：新设计直接形成具体结构；成熟稿核对整理，只补真实缺项，不为typed收据重做。一个整合方向投影到四类用途/各状态，分阶段按需更新，见[文档合同](prompt-document.md)。

## 当前画面与一次核对

确定画幅、状态、实际参考职责与可见范围，先写完整布局与视觉主次，再写具体结构。头像不塞鞋背面，执行图不删应入画小件。已选骨点、左右、比例、片数、叠压连接、色材、佩戴及状态不静默改；允许同义、合句、去理由和重复，主次不授权删结构。

无实际旧图作编辑参照的文生图只描述当前几何/当前值，不写首稿、before→after或旧数值。有真实待改图才可指图说明变化和保持项。历史由后台版本保存，不为表达整理新增审批。

正文自足可复制，不仅summary、标签或“同上”。用户明确画幅优先，身体7.3头身/肩髋比不是画布比例。完成后一次核硬要求、结构、状态与跨类连续性，普通任务不额外造inventory/coverage/results表。默认唯一文档，工具派生JSON/TXT和来源/版本；明确只对话时仍交完整词。候选词无图可完成，不造已批参考，程序不证明语义、美感或看图。

## 旧typed与正式来源：保留原合同

本节仅用于明确legacy_typed、旧scope、typed来源或正式生产；普通prompt_document不先转typed/freeze。已有真实约束不静默降级。CharacterPromptPackageV1保留prompt-package.json与机械TXT，TXT逐字等于prompts[].text以两个换行连接、末尾一个换行。

正式沿当前已批design_basis/anchor_images和原preview例外；旧无新标记继续原合同。旧独立冻结候选用purpose:candidate和task_frozen_delivery，path、sha256、inputs_path、inputs_sha256真实且task/package同源。冻结见[专项旧合同](specialist-contract.md)，不写active或继承批准，错误工程不降独立。

旧明确纯text候选沿delivery_mode:text、purpose:candidate、task_text_design{text,source_ref}传实际完整设计；text_sha256可选且核真实UTF-8，preserve须在原文，不让用户填表。代码不证明消息真实性、成熟度或完整语义，也不提供正式批准/锚点。

正式新阶段仍保存payload.prompt_detail_contract及真实专项采用，旧逐cue检查继续。显式fidelity_review:PromptFidelityReviewV1由prompt_fidelity.py列真实inventory并核版本、实际span及数值/左右/数量/状态。review保留source_sha256、prompt_sha256、semantic_review、coverage；原样完整出现自动核覆盖，同义改写才需mapping，模型仍核语义。不得省review却声称使用同义保真分支。

## 版式与实际回图

保留3:4头像、九宫格、9:16中性模卡及[执行版式](execution-sheet.md)，群演/非人走各自分支。人形执行正文先写9:16、2×2、上约1/3下约2/3及四格裁切，再写衣装；左下颈肩以下至鞋且头彻底出画，右下头至鞋完整背面，不能上下各半或漏手鞋。

获授权用同一已展示词生成，生成前仅轻量格式检查；生成后直接交用户人工看，默认不自动审图、局部修补、复核或重跑。明确请求审图才实际查看，明确请求编辑才修改；不自称图片通过，程序不代表成图执行。
