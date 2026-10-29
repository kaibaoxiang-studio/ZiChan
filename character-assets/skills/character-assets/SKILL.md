---
name: character-assets
description: "从剧本、小传或已有稿交具体角色设计和提示词，按需接正式资产生产"
---

# 角色资产主控

先判断用户本次要讨论、设计、修改、提示词还是正式资产；从请求和已有材料确定范围，不另问一轮内部模式。没有正式工程也能完成具体设计与候选词；实际传入错误 `project_root` 时说明错误，不静默转独立模式。

执行一条主链：读取或复用人物理解 → 确定设计意图 → 实际采用当前相关专项方法 → 整合并核对本次要求 → 交完整设计／提示词 → 按需登记生产。已有成熟稿从复核或编译接续；缺结构只补缺处。完整人物可跨脸发、体态与衣装，局部请求不重做全员。详见[请求路由](../../references/routing-and-integration.md)；新创作先读[人物方法](../../references/director-understanding.md)，按问题查[知识索引](../../knowledge/index.md)，不全量加载。

普通细节主动推荐后集中审阅；改变身份、剧情信息或已批方向的重要决定才集中提出。常规专项由主控 inline 实际执行，复杂冲突才会诊。每项工作应形成针对人物的可画结构与取舍，不能以标签、路由清单或读过资料冒充设计。

人默认只用一份持续更新的**角色设计文档**：当前具体设计、修改结果、当前完整可复制提示词；图片单独。后台保留标准 JSON、同源 TXT、来源、版本与执行记录，不把中间稿和审计文件堆交给用户。提示词默认生成 JSON＋同源 TXT 并提供可读正文，只有本次明确只要对话文字才省文件；不能自行降交付。

已批人物试改只写 task-local draft，正式父约束只读；确认采用前不 submit 覆盖 active、不使生产图失效。采用后沿现有登记批准规则复核受影响图片。[专项与交付](../../references/specialist-contract.md)规定实际返回；[提示词保真](../../references/prompt-detail-contract.md)规定已选入画结构不丢，允许同义编译。

正式生产才加载[工作流](../../references/workflow.md)、[阶段与批准](../../references/phased-design.md)和[接口](../../references/interfaces.md)。保留头像3:4、全身9:16、模卡、常规四图与群演单图分支、旧批准和 ephemeral 隔离。无图不报视觉通过；有图实际查看后审查，用户确认后才作为正式锚点。不自行生图；明确授权且会话工具可用时按同一已展示正文生成候选。

## Packaged references

- [references/routing-and-integration.md](../../references/routing-and-integration.md)
- [references/director-understanding.md](../../references/director-understanding.md)
- [knowledge/index.md](../../knowledge/index.md)
- [references/specialist-contract.md](../../references/specialist-contract.md)
- [references/prompt-detail-contract.md](../../references/prompt-detail-contract.md)
- [references/workflow.md](../../references/workflow.md)
- [references/phased-design.md](../../references/phased-design.md)
- [references/interfaces.md](../../references/interfaces.md)
