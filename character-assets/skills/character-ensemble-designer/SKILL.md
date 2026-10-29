---
name: character-ensemble-designer
description: "群演单图设计师：有台词单人执行图与无台词群像图"
---

# 群演单图设计师

候选与批量同样先完成可画设计。新提示词及验收项须逐条承接已批准的逐人脸发、体态、衣装、色材和道具动作，不能用“普通制服”“各有差异”等概括替代；一套备选的完整设计不抵另一套的遗漏。明确人数按本资产原文局部核实，资产名带“三个”或“群像”后缀仍须正确识别，其他物件数字不算人数。

有台词角色的单图路线按 morphology 适配：human（旧默认）/humanoid 为一张 9:16 四格；nonhuman 用 SpeakingExtraDesignV1 的具体 morphology_details 和已批准 execution_layout（含可入正文的 description），仍只一张 9:16。非人不强填人脸、发型或无头服装，提示词继承同形态、布局和实际结构，审查按本形态核对。其余人物/群像路线不增加图片阶段。

读取 [群演单图合同](../../references/group-ensemble.md)、[群像差异化框架](../../references/differentiation-framework.md) 与 [图像提示词](../../references/prompting.md)。先以 scripts/character_project.py plan 的 asset_mode 判定路线。speaking_extra 有指定台词，每状态只做一张 9:16 执行资产，人形四格、非人按已批准形态布局并独立打包；ensemble 无台词群演群像，每状态只做一张完整全身群像图。两者均不制作头像、九宫格、全身模卡或独立穿衣圣经。从标准剧本原文核对人数、行动、职业/群体功能、道具和所在世界；从已批准 ProjectVisualBibleV1 读取整套项目风格，不能沿用参考文档的插画画风或固定 21:9。有明确人数就逐人对应；不明确就按单画布辨识度选择代表人数并标注是创作选择。每个画中人写站位、体型姿态、脸发、衣装结构与材质、行动/道具，保证共性属于同组，差异能在缩略图辨认。一张画布按左至右定序，每人全身可见、不重叠、不裁脚，道具归属清楚；多人用依人数和可辨识度选定的横版比例，单人用 9:16 全身。无台词组保存 GroupEnsembleDesignV1；有台词者保存 SpeakingExtraDesignV1，须对照原文台词与人物行动，人形具体设计脸发体态、正式服装正背结构及道具，采用正脸/45°/无头正面服装/完整背面四格；非人按上文形态字段和已批准布局执行。两类均集中审阅文字，获批后生成只含 execution 的 CharacterPromptPackageV1；一张图一次实际审图与操作者批准，分别打包 CharacterEnsemblePackV1 或 CharacterSpeakingExtraPackV1。只取参考文档的群像编排形式；剧本和获批美术基准决定世界、配色、媒介与真实度。

## Packaged references

- [knowledge/index.md](../../knowledge/index.md)
- [references/group-ensemble.md](../../references/group-ensemble.md)
- [references/differentiation-framework.md](../../references/differentiation-framework.md)
- [references/prompting.md](../../references/prompting.md)
- [references/review.md](../../references/review.md)
- [references/interfaces.md](../../references/interfaces.md)
