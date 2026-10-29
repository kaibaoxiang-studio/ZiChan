# 角色资产知识检索 v0.2.16

先理解本次人物与交付，再选相关方法；本索引是检索目录，不是必读清单。现有58份锁定知识快照保留原文与来源。人物事实、用户明确选择和已批准边界优先；来源中的个案、固定件数、性别阶层配搭及比例公式不自动成为通用要求。

| 当前问题 | 先用的方法／Skill | 按需知识 |
| --- | --- | --- |
| 全文人物理解、定位、世界与观众信息 | [人物总控](../references/director-understanding.md) | 有效全文上下文先复用；新全文实际阅读，不用标签替代 |
| 完整人物、头像、局部修改如何交付 | [请求路由](../references/routing-and-integration.md)、[具体设计](../references/design-detail-standard.md) | 只做当前维度；不默认让完整形象缩成头像 |
| 原创脸、五官与45°连续 | `$character-face-design` | `original-face`、`face`；缺术语再取06脸型、08眉、09眼、10耳、11鼻、12唇 |
| 发型、发流、打理与前侧后体积 | `$character-hair-design` | `hair`；名称检索取07发型 |
| 肤色、局部光泽与可见纹理 | `$character-skin-design` | `skin`、14皮肤材质、15面部毛发；油光／压印问题再读该专项anti-stereotype-texture |
| 稳定标记、妆容、临时表面 | `$character-face-decoration-design` | `face-decoration`、13妆容；状态妆取`character-costume-designer/state-makeup` |
| 头耳颈识别、饰品有无与佩戴 | `$character-face-signature-design` | `face-memory`、16头耳颈；物件明确后再取17头戴、18面部穿戴、20颈部 |
| 头身／肩胯／肢段／体块与动作 | `$character-body-design` | `body`、`body-proportion-3d`；非人下肢才取31特殊下肢 |
| 世界环境、技术、资源如何影响外观 | `$character-world-appearance-design` | `world-appearance`，用实际接触机制，不能推定族群或人格 |
| 主锚点、安静区与近邻撞型 | `$character-feature-focus`、`$character-cast-differentiation` | `feature-focus`、`ensemble`；旧占用表按需取`legacy-visual` |
| 人物衣装及剧情状态 | `$character-costume-designer`、[服饰方法](../references/costume-designer.md) | `costume-deep`，具体状态再取`state-makeup` |
| 服饰品类、衣层与廓形 | `$character-costume-style-design` | `costume-style`；21上身、26贴身、27下装、29袜护、30鞋按物件取 |
| 衣片、叠压、连接、开合与活动量 | `$character-costume-cut-design` | `costume-cut`；重点部件取[物件方法](../references/costume-component-design.md) |
| 衣装色块与材料行为 | 配色／材质专项 | `costume-color`／`costume-material`；保持当前已选物件，不因词表重配全身 |
| 衣身、四肢独立穿戴与道具接口 | `$character-costume-accessory-design` | `costume-accessory`；22手腕、23腰、24臂、25背、28腿按部位取 |
| 单图群演、无台词群像或非人 | `$character-ensemble-designer`、[群演合同](../references/group-ensemble.md) | 按明确人数与已选形态，不全套人形四图 |
| 设计到提示词、参考职责与同源交付 | [提示词保真](../references/prompt-detail-contract.md)、[出图规则](../references/prompting.md) | `character-image-prompt/hedgehog-general-image-skill`，媒介转换明确获选才取`hedgehog-2d3d` |
| 实际回图审查／局部修图 | [审图](../references/review.md)／[修图](../references/editing.md) | 当前能力的feature-focus／anti-stereotype／hedgehog快照按具体缺陷取 |
| 正式项目、依赖、批准与最终资产表 | [工作流](../references/workflow.md)、[接口](../references/interfaces.md) | [分阶段](../references/phased-design.md)、[最终资产表](../references/final-asset-table.md)仅进入生产时加载 |

每个专项SKILL列出完整快照链接。先用具体方法产生人物化结果，再留必要“问题→方法→结果→采用位置”记录；不以读取路径数量证明设计完成。来源与哈希见知识锁与sources.lock，原始集中源库不随运行重新采集。[苏老太案例](../references/prompt-density-example-su.md)示范完整性与状态切换，不是全员密度或造型下限。
