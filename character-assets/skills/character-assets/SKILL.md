---
name: character-assets
description: "角色资产主控：从剧本依据到可复用角色资产包"
---

# 角色资产主控

先读 [知识索引](../../knowledge/index.md)，按情景只加载本轮需要的 reference。

使用 [工作流](../../references/workflow.md) 与 [接口](../../references/interfaces.md)。先定位用户项目和当前阶段；没有项目时用内置 scripts/character_project.py 导入标准剧本与资产表，场记可选。从角色清单做第 -1 阶段视觉基准和全员轻规划；用群像差异化总控建立比较组与五轴矩阵，对发型、体型、五官、皮肤和服饰按缺口调用专项，而非让所有角色强制走十轮。提交重点人形卡必须写清脸、发、体态、皮肤、服饰和饰件的可画细节，列十专项的采纳结果或不启用理由。主角与重要角色分轮 Grill Me，普通角色分层处理；已批准角色不因新方法自动重做。每轮只推进一个已授权且依赖已批准的阶段；及时提交结构化 JSON 并通过 CLI 记录批准、图片、审查和来源。本插件只写 GPT Image 2.5 提示词，不调用生图工具。用户回图后必须实际查看图片，通过审查与操作者确认后才进入下一阶段。新细节先提议，获批后修改设计卡。头像默认 3:4 竖版，只有操作者明确要求才更改。仅在四阶段均通过时打包。运行中报告实际文件路径、未解决疑点与下一步；不虚报成图质量。

## Packaged references

- [knowledge/index.md](../../knowledge/index.md)
- [references/workflow.md](../../references/workflow.md)
- [references/interfaces.md](../../references/interfaces.md)
- [references/evidence.md](../../references/evidence.md)
- [references/source-notes.md](../../references/source-notes.md)
- [references/differentiation-framework.md](../../references/differentiation-framework.md)
- [references/specialist-contract.md](../../references/specialist-contract.md)
- [references/design-detail-standard.md](../../references/design-detail-standard.md)
- [references/render-texture-standard.md](../../references/render-texture-standard.md)
