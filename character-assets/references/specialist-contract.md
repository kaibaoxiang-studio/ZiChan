# 专项方法与交付边界 v0.2.17

人物理解形成意图，专项方法形成可画结构，完整提示词直接承载设计。方法、生产记录和用户批准不同，读过路径或写used不能冒充设计，过程收据不能证明美感。

## 普通路径

按当前问题用相关Skill与必要知识，常规主控inline形成一个整合推荐；跨域结构冲突、复杂形体工艺或反复失败才独立会诊。真实会诊留实际返回，不把inline伪写independent；不要求十三会话、十三项计划或方法台账。

成果直接更新[角色提示词文档](prompt-document.md)。不前置长设计稿、CharacterDesignDeliveryV1、body_form对象、rules_applied、knowledge_refs/SHA、逐field results、PromptDetailContract或freeze。保留的是具体骨点、比例、衣片连接、色材及状态。成熟稿只补真实缺项；局部只改受影响词，未改决定原文继承。

不把新增外观伪称原文，影响剧情的事实留真实定位，不给每个眉眼打证据标签。解释、弃选、旧值不入词。工具自动维护来源/版本/TXT，模型不手编hash/父引用/批准。普通旧工程试改只读，不写active或撤销旧图批准。

## 兼容旧typed交付：明确调用时才使用

以下只用于delivery_contract:legacy_typed、显式旧scope、typed来源或正式生产。普通文档不先转这些对象过门；真实旧typed任务不能用普通文档替换并声称满足旧合同。

CharacterDesignDeliveryV1外层仍schema_version、kind、scope、data；独立StandaloneCharacterDesignV1保留subject、真实sources、understanding、design_thesis、payload、specialist_execution、deferred_dimensions、unresolved。requested_dimensions只约束旧requested分支，不新增生产scope。来源绑定真实request和文件SHA；provided/captured标真实来源，不补假历史。文件仍design-result.json与机械design.md，旧prompt-package.json与TXT同源。

旧typed候选需ledger外冻结时用真实CLI：
~~~sh
python scripts/character_project.py freeze-design --file /internal/design-result.json --inputs /internal/inputs.json --output /internal/frozen
python scripts/verify_design_delivery.py render --design /internal/design-result.json --output /internal/design.md
~~~

工具自动校验并返回design_source实际path、sha256、inputs_path、inputs_sha256，不能手编SHA或把设计自带task当真实inputs。局部typed稿用可重复--base-design绑定同人物真实JSON；local base不能覆盖正式父约束。--markdown只指所选JSON对应稿，未给则机械生成。旧document命令继续服务其视图，不是普通文档默认；text仍交真实正文，不假报文件/哈希，后续转录标captured_from_conversation，不倒填批准/执行。

## 正式阶段继续原合同

正式direction/stage/legacy_card继续真实ID、父SHA与批准约束，见[阶段](phased-design.md)和[接口](interfaces.md)。新CharacterStageDesignV1.2/execution_contract_version:2的inline保留实际knowledge_refs/SHA、rules_applied、results；independent保留真实proposal_ref/SHA、所选方案和applied_elements。defer激活写任务/原因，状态妆发按需激活而不换基础身份。

正式cue解析到实际results/applied_elements、execution_layout或已批父记录，原文事实不冒充专项成果。知识在成功提交时归档；旧批准继续原合同，升级不强迫重做。

真实独立生产提案沿CharacterSpecialistProposalV1.2，含task、knowledge_refs、facts、options、recommended_option_id、unresolved及不适用理由。机器允许1–3方案、每方案至少两个可画元素；不代表普通首稿要多方向。默认一个整合推荐，实际有比较必要才用额外方案。真实调用运行validate_specialist_proposal.py，旧V1/V1.1回读。

正式采用后才submit/approve并复核实际受影响图，无变化转录不另加仪式；不能代用户批准。来源、结构和字面一致不证明理解或美感，生成图直接交用户看，默认不自动审图、修补或重跑；明确请求审图才实际查看，不代用户批准。
