---
name: scene-image-prompt
description: "从已批准场景卡编写外部静帧提示词"
---

# 场景静帧提示词

先读 [知识索引](../../knowledge/index.md)，按任务加载本轮 reference。

读取 [提示词方法](../../references/prompting.md)、当前已批准视觉基准与设计卡。参考图逐张标职责；列场景事实、空间主次、活动区域、尺度、材料光线、不变量和回图检查点。当前场景已批准幻想尺度时才加载专项知识。输出 ScenePromptPackageV1 并通过 scripts/scene_project.py submit 合同检查；交操作者外部出图。不写 Midjourney 固定参数，不调用生图 API。

## Packaged references

- [knowledge/index.md](../../knowledge/index.md)
- [references/prompting.md](../../references/prompting.md)
- [references/interfaces.md](../../references/interfaces.md)
- [references/knowledge/chinese-fantasy-scale.md](../../references/knowledge/chinese-fantasy-scale.md)
