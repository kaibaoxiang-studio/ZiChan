---
name: character-assets
description: "角色资产主控：从剧本依据到可复用角色资产包"
---

# 角色资产主控

先读 [知识索引](../../knowledge/index.md)，按情景只加载本轮需要的 reference。

使用 [工作流](../../references/workflow.md) 与 [接口](../../references/interfaces.md)。先用 [需求路由与整合](../../references/routing-and-integration.md) 标定单张或批量范围、当前状态与前置门槛。先定位用户项目和当前阶段；没有项目时用内置 scripts/character_project.py 导入标准剧本与资产表，场记可选。从角色清单做第 -1 阶段视觉基准和全员轻规划；用群像差异化总控建立比较组与五轴矩阵，先形成逐人专项路由，再对特征焦点、发型、体型、五官、皮肤和服饰按缺口实际调用专项；每个 used 项保存有效提案和所选方案。提交重点人形卡必须写清脸、发、三维体块、皮肤、服饰和饰件的可画细节；身体要有头身数值与其余骨点参照，不能只写身高体重或修长。列十三专项的采纳结果或不启用理由，并记录环境技术影响与面部表面状态。主角与重要角色分轮 Grill Me，普通角色分层处理；已批准角色不因新方法自动重做。每轮只推进一个已授权且依赖已批准的阶段；及时提交结构化 JSON 并通过 CLI 记录批准、图片、审查和来源。本插件只写 GPT Image 2.5 提示词，不调用生图工具。用户回图后必须实际查看图片，通过审查与操作者确认后才进入下一阶段。新细节先提议，获批后修改设计卡。头像默认 3:4 竖版，全身图默认 9:16 竖版，只有操作者明确要求才更改。人形头像与表情以脸为主体，可取完整头部、双肩及上胸，不固定裁到锁骨以上；服装不入画用 face_only，上胸入画用对应白色背心，整组模式一致；全身图用白色背心、短裤、赤脚作模卡参考，执行资产表恢复已批准正式服装。新项目依次完成头像、九宫格、全身模卡、每状态服饰设计图、执行资产图；每张图按资产名命名，逐图通过后才打包。旧项目沿用原四阶段。运行中报告实际文件路径、未解决疑点与下一步；不虚报成图质量。

## Packaged references

- [knowledge/index.md](../../knowledge/index.md)
- [references/workflow.md](../../references/workflow.md)
- [references/interfaces.md](../../references/interfaces.md)
- [references/routing-and-integration.md](../../references/routing-and-integration.md)
- [references/costume-design-stage.md](../../references/costume-design-stage.md)
- [references/model-card-baseline.md](../../references/model-card-baseline.md)
- [references/evidence.md](../../references/evidence.md)
- [references/source-notes.md](../../references/source-notes.md)
- [references/differentiation-framework.md](../../references/differentiation-framework.md)
- [references/specialist-contract.md](../../references/specialist-contract.md)
- [references/design-detail-standard.md](../../references/design-detail-standard.md)
- [references/render-texture-standard.md](../../references/render-texture-standard.md)
- [references/feature-focus-and-body-form.md](../../references/feature-focus-and-body-form.md)
