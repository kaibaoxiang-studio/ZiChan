# 角色资产知识检索 v0.2.20

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
| 单方向提示词设计、参考职责与同源交付 | [持续提示词文档](../references/prompt-document.md)、[出图规则](../references/prompting.md) | `character-image-prompt/hedgehog-general-image-skill`；旧正式合同才取提示词保真；媒介转换明确获选才取`hedgehog-2d3d` |
| 用户明确要求的审图／局部修图 | [审图](../references/review.md)／[修图](../references/editing.md) | 默认生成后直接展示，不自动审图或重跑；明确反馈后按具体缺陷取方法 |
| 正式项目、依赖、批准与最终资产表 | [工作流](../references/workflow.md)、[接口](../references/interfaces.md) | [分阶段](../references/phased-design.md)、[最终资产表](../references/final-asset-table.md)仅进入生产时加载 |

每个专项SKILL列出完整快照链接。普通路径将采用的具体设计直接写进当前完整提示词；不另写逐专项方法收据、独立设计长稿或冻结证明。真实会诊或明确旧正式合同才保留相应返回物；不以读取路径数量证明设计完成。来源与哈希由程序维护，原始集中源库不随运行重新采集。[苏老太案例](../references/prompt-density-example-su.md)示范完整性与状态切换，不是全员密度或造型下限。

## v0.2.20 定点可操作参考

款式仅有类别或功能模板时，读[款式语汇](../references/knowledge/character-costume-style-design/costume-style.md)的形状/比例/衣层与穿法对照；形式、纹样与纯审美转译读[深层服饰](../references/knowledge/character-costume-designer/costume-deep.md)；附加穿戴的形底/节奏读[饰品关系](../references/knowledge/character-costume-accessory-design/costume-accessory.md)。按当前问题取所需段落，不全库扫描，不以读过文件数量证明设计。

本次保持58快照，定点更新上述三份与world-appearance。款式/饰品由原ZIP选章重新捕获；深层与环境课程本轮未重新取得原文，以原锁定快照和用户新授权增量维护。原archive记录、选章hash与本次rules修订见archive-manifest，集中来源留工作区，发布包只带精炼规则。族裔方向可用于虚构人物原创，不以现实姓名/图像推断身份或血统事实。
