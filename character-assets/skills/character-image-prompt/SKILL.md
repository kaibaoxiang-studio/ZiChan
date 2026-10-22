---
name: character-image-prompt
description: "把已批准设计转成 GPT Image 2.5 分阶段提示词"
---

# 图像提示词

先读 [知识索引](../../knowledge/index.md)，按情景只加载本轮需要的 reference。

读取 [出图规则](../../references/prompting.md) 与当前阶段规则。先检查已批准卡是否具象，空泛则回设计轮补细；按真实质感规则选择适量可见肌理和材料词。只使用已批准设计卡及当前选定图片，按画幅抽取主锚点，标注每张参考图的身份/服装/风格职责。背景也是设计维度：无明确批准时仅用无场景、无纹理的中性底色作核对背景；不得自行加入地点、建筑、地貌、天气或借光线描述暗示剧情场景。头像默认 3:4 竖版且每条提示词写明比例，只有操作者明确指定才覆盖；产 2–3 条同设计候选；人形头像与表情优先锁骨以上、服装不入画，受阻时记录原因并整组换对应白色背心；表情按剧情选 9/16 格且图内写中文标签；全身图默认 9:16 竖版，每条提示词与验收项写明比例，穿对应白色背心、短裤并赤脚，头到双脚完整并留边界，逐条继承已批准设计卡中的头身、肩胯与腿身关系并核对；人形执行表恢复正式服装，按上正脸/45°半侧脸、下无头放大正面服装/完整背面四格。非人使用已批准替代布局。输出 CharacterPromptPackageV1 与检查点，经 CLI 合同校验后交操作者外部出图。

## Packaged references

- [knowledge/index.md](../../knowledge/index.md)
- [references/prompting.md](../../references/prompting.md)
- [references/model-card-baseline.md](../../references/model-card-baseline.md)
- [references/expression.md](../../references/expression.md)
- [references/execution-sheet.md](../../references/execution-sheet.md)
- [references/interfaces.md](../../references/interfaces.md)
- [references/design-detail-standard.md](../../references/design-detail-standard.md)
- [references/render-texture-standard.md](../../references/render-texture-standard.md)
- [references/knowledge/character-image-prompt/feature-focus-prompt.md](../../references/knowledge/character-image-prompt/feature-focus-prompt.md)
- [references/knowledge/character-image-prompt/hedgehog-2d3d.md](../../references/knowledge/character-image-prompt/hedgehog-2d3d.md)
- [references/knowledge/character-image-prompt/hedgehog-general-image-skill.md](../../references/knowledge/character-image-prompt/hedgehog-general-image-skill.md)
- [references/knowledge/character-image-prompt/anti-stereotype-texture.md](../../references/knowledge/character-image-prompt/anti-stereotype-texture.md)
