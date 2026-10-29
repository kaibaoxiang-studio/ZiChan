---
name: character-image-review
description: "仅在用户明确要求时审查目标图片的事实、身份、结构与版式"
---

# 明确请求时的回图审查

默认生成后直接交用户看，不自动审图、修补、复核或重跑。只有用户明确要求审图/核对目标图片或相应正式审查登记时使用本Skill，不能作为普通生成交付的前置。

实际打开目标图、当前完整提示词与实际提供的参考；正式旧工程再读真实阶段/卡/锚点。不为首次头像或群演虚构上游图。按[审查规则](../../references/review.md)先看画幅/整体布局，再看身份、比例、剪裁、色材、佩戴、状态、标签和背景；无法看清写uncertain，不从提示词禁令推成图通过。

人形执行图按[精确版式](../../references/execution-sheet.md)：9:16、2×2、上约1/3下约2/3，左上正脸、右上约45°、左下颈肩以下至鞋且头彻底出画/手鞋完整、右下头到鞋完整背面且尺度可读。上下各半、左下只到大腿/缺手鞋、残头或背图太小应明确列问题，不能说“基本符合”后只修字。群像/非人按实际分支。

头像查3:4/头颈肩安全边界与五官发际；表情核格数/中文/同一身份；全身核9:16/完整头手脚及提示词五组比例。新状态核同一脸体、妆发、衣装前背连接与鞋饰，未见视角不宣称验证。详见[头像尺度](../../references/avatar-identity-granularity.md)和[状态方法](../../references/scene-styling-needs.md)。

普通审图用简短具体反馈；用户明确要正式记录才沿CharacterImageReviewV1保存真实结果，不另造长台账。不自动修图或重新生成，修改须用户明确要求。正式批准仍由用户决定，模型审查和程序通过都不能代替批准。

## Packaged references

- [references/review.md](../../references/review.md)
- [references/execution-sheet.md](../../references/execution-sheet.md)
- [references/avatar-identity-granularity.md](../../references/avatar-identity-granularity.md)
- [references/scene-styling-needs.md](../../references/scene-styling-needs.md)
