# 角色资产知识索引 v0.1

先读取当前任务对应的 reference，不要在每次调用中加载整个知识库。任何 reference 的示例都只是方法，剧本事实与操作者已批准的决定优先。

| 情景 | 加载 | 用途 |
| --- | --- | --- |
| 项目启动、全员规划 | `references/evidence.md`、`references/character-design.md` | 建立第 -1 阶段视觉基准、角色清单与差异化方向 |
| 逐人设计、Grill Me | `references/character-design.md`、`references/costume-and-morphology.md` | 将世界规则转成可见设计，处理服装、非人和极端体型 |
| 剧本与三份输入冲突 | `references/evidence.md` | 按原文证据优先列疑点，不暗改事实 |
| 头像、全身图提示词 | `references/prompting.md` | 从已确认设计卡抽取可见锚点，指定参考图职责 |
| 外部出图的通用提示词结构与原样中文 | `references/knowledge/character-image-prompt/hedgehog-general-image-skill.md`、`references/prompting.md` | 区分新图/编辑，控制补充细节，逐张标注参考图职责 |
| 已批准的 2D→3D 呈现 | `references/knowledge/character-image-prompt/hedgehog-2d3d.md`、`references/prompting.md` | 保留身份与服装，只转换已批准的媒介、材质和光照 |
| 表情资产 | `references/expression.md`、`references/prompting.md` | 根据剧情选 9 或 16 个表情并生成图内中文标签 |
| 执行资产表 | `references/execution-sheet.md`、`references/prompting.md` | 人形 2×2 精确版式及非人适配 |
| 回图审查 | `references/review.md` | 核对事实、身份、版式、标签并分类阻断问题 |
| 局部修图 | `references/editing.md` | 描述目标区域、改变内容、保留内容与禁改内容 |
| 单项修图与回流重审 | `references/knowledge/character-image-edit/hedgehog-general-image-prompting.md`、`references/editing.md` | 每轮修一项，重申身份和其他格位不变量，再审查整张图 |
| 上游改版 | `references/workflow.md`、`references/evidence.md` | 比较输入版本并局部重开受影响的资产 |

本索引只描述何时加载。每份规则的出处、采用方式和未采用内容见 `references/source-notes.md` 与插件根目录 `sources.lock.json`。历史服装知识是灵感入口；需要具体时代准确性时另查可靠材料，记录查证位置。
