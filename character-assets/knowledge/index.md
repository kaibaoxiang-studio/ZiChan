# 角色资产知识索引 v0.2.1

先读取当前任务对应的 reference，不要在每次调用中加载整个知识库。任何 reference 的示例都只是方法，剧本事实与操作者已批准的决定优先。

| 情景 | 加载 | 用途 |
| --- | --- | --- |
| 项目启动、全员规划 | `references/evidence.md`、`references/character-design.md`、`references/differentiation-framework.md`、`references/knowledge/character-cast-differentiation/ensemble.md` | 建立第 -1 阶段视觉基准、比较组与五轴矩阵；旧 Skill 的占用表方法按需加载 `legacy-visual.md` |
| 逐人设计、Grill Me | `references/character-design.md`、`references/costume-and-morphology.md`、`references/specialist-contract.md` | 先定位具体缺口，再调用下表的专项，避免全员强制走完所有岗位 |
| 新建重点人形设计卡过于概括 | `references/design-detail-standard.md`、`references/knowledge/character-design/anti-stereotype-texture.md` | 六组具象细节、十专项实际成果与 V2.1 卡门槛 |
| 剧本与三份输入冲突 | `references/evidence.md` | 按原文证据优先列疑点，不暗改事实 |
| 头像、全身图提示词 | `references/prompting.md` | 从已确认设计卡抽取可见锚点，指定参考图职责 |
| 油亮、蜡感、材质空泛或脏糊 | `references/render-texture-standard.md`，再按设计/提示词/审查/修图的对应 `anti-stereotype-texture.md` 快照加载 | 分开设计层与渲染层；按媒介、证据和回图缺陷选词与修复 |
| 外部出图的通用提示词结构与原样中文 | `references/knowledge/character-image-prompt/hedgehog-general-image-skill.md`、`references/prompting.md` | 区分新图/编辑，控制补充细节，逐张标注参考图职责 |
| 已批准的 2D→3D 呈现 | `references/knowledge/character-image-prompt/hedgehog-2d3d.md`、`references/prompting.md` | 保留身份与服装，只转换已批准的媒介、材质和光照 |
| 表情资产 | `references/expression.md`、`references/prompting.md` | 根据剧情选 9 或 16 个表情并生成图内中文标签 |
| 执行资产表 | `references/execution-sheet.md`、`references/prompting.md` | 人形 2×2 精确版式及非人适配 |
| 回图审查 | `references/review.md` | 核对事实、身份、版式、标签并分类阻断问题 |
| 局部修图 | `references/editing.md` | 描述目标区域、改变内容、保留内容与禁改内容 |
| 单项修图与回流重审 | `references/knowledge/character-image-edit/hedgehog-general-image-prompting.md`、`references/editing.md` | 每轮修一项，重申身份和其他格位不变量，再审查整张图 |
| 上游改版 | `references/workflow.md`、`references/evidence.md` | 比较输入版本并局部重开受影响的资产 |

本索引只描述何时加载。每份规则的出处、采用方式和未采用内容见 `references/source-notes.md` 与插件根目录 `sources.lock.json`。历史服装知识是灵感入口；需要具体时代准确性时另查可靠材料，记录查证位置。

## 0.2.0 专项知识加载

| 缺口 | Skill 与知识快照 |
| --- | --- |
| 发际、发流、发型块面与背面 | `$character-hair-design` → `references/knowledge/character-hair-design/hair.md` |
| 年龄比例、骨架、体重分布、体态 | `$character-body-design` → `references/knowledge/character-body-design/body.md` |
| 五官与脸部骨相、模板脸 | `$character-face-design` → `references/knowledge/character-face-design/face.md` |
| 面部记忆点、发耳颈饰 | `$character-face-signature-design` → `references/knowledge/character-face-signature-design/face-memory.md` |
| 皮肤纹理、光泽、生活痕迹 | `$character-skin-design` → `references/knowledge/character-skin-design/skin.md` |
| 衣装品类、长度、松紧与层次 | `$character-costume-style-design` → `references/knowledge/character-costume-style-design/costume-style.md` |
| 结构线、缝接与活动余量 | `$character-costume-cut-design` → `references/knowledge/character-costume-cut-design/costume-cut.md` |
| 衣装主辅色和色块 | `$character-costume-color-design` → `references/knowledge/character-costume-color-design/costume-color.md` |
| 纤维/皮革/金属表面与磨损 | `$character-costume-material-design` → `references/knowledge/character-costume-material-design/costume-material.md` |
| 衣身、腰、手与随身穿戴饰品 | `$character-costume-accessory-design` → `references/knowledge/character-costume-accessory-design/costume-accessory.md` |

群像差异化总控是横向审查，不代替以上专项。每个技能只加载本轮相关知识快照；同一件越过锁骨的饰品由主控指定唯一主责。

0.2.1 新增《拒绝脸谱化人物设计》来源的 7 份定点快照：`character-design`、`character-cast-differentiation`、`character-skin-design`、`character-costume-material-design`、`character-image-prompt`、`character-image-review`、`character-image-edit`。头像 3:4 规则在 `references/prompting.md` 和 CLI 提示词包合同中，回图按 `references/review.md` 核对。
