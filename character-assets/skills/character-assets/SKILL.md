---
name: character-assets
description: "自主完成人物化设计并交付单方向角色提示词，成熟稿按限定范围保真整理；支持已有图资产表"
---

# 角色资产主控

收到“最终资产表、已有图插表、嵌图汇总、整理交付”时，先走[图片资产表交付](../../references/final-asset-table.md)：复用既有清单、稳定ID/状态与实际图片，只做映射、嵌图和缺口说明；不重新提取、重做美术基准或创作、自动审图/重跑。此路由不要求先交提示词文档或建立正式项目。只有当前确实需要创作/改词时才走下文。

从请求和材料确定人物、状态与所需画面，不另问内部模式。新建角色先判断适用的物种、族裔与外貌背景；多族裔世界或用户要求多人种时，总控按世界与人物关系主动安排新建虚构角色的族裔/混合背景及外貌组合，不按姓名默选单一族群或硬凑配额；物种、人类族裔和文化地域背景分开，规则见[人物方法](../../references/director-understanding.md)。采用的背景写入各独立提示词，仍具体设计脸发肤色；局部换装不重选已定身份。默认一个整合推荐方向，普通细节主动决定；真正硬冲突、重大新增剧情设定或改变已批身份才集中提出。四类词是同一方向的用途投影，不是四套方案，不外显A/B/C与未选取舍。

新建角色先由人物总控自主形成创作命题和完整设计决议，再表达为可复制提示词；这是同次创作内的先后，不多交一份设计长稿。仅需提示词时不外显过程。完整决议不能由短立领、深色制服等类目模板代替；不要求1000字符或强加复杂饰物。人只用一份持续更新的**角色提示词文档**：头像、表情、全身模卡、各状态执行图；按当前委托完成或逐阶段追加，局部不补跑整套。读[普通交付](../../references/prompt-document.md)取得上下文与保存方法。

新创作先用[人物方法](../../references/director-understanding.md)理解或复用同版本材料，决定观众应读到的形象、重点与隐藏，再按[知识索引](../../knowledge/index.md)运用当前设计域的基础方法。知识不是失败后的补救：有明确设计难题时继续读对应参考并解决。专项接收具体问题和保持项，不只接“补脸/发/剪裁”的维度名单；常规由主控inline执行，复杂跨域结构才独立会诊。批量主要角色逐人完成连贯决议并表达，不把同一造型替换姓名色彩后当作全员完成。保留22项能力与58份知识。服饰交[服饰设计师](../character-costume-designer/SKILL.md)依人物读法、reference转译与整体造型主张组织专项，而非填五项部件清单。结果须有可画脸发、五组身体比例、衣片连接与色材，不能退成“清秀、干练、真实”。一次核对本次硬要求、结构、主次与跨画面一致性，详见[具体标准](../../references/design-detail-standard.md)。

成熟稿直接复核接词，缺哪处只补哪处；局部先读当前文档，只更新受影响词，未改内容原文保留。工具机械维护版本、来源及TXT，模型只写本次提示词update，不手编hash、父引用或执行台账。理由、弃选与旧值不塞可复制正文。

图片与文字分开：无图可交候选词，不等待上游正式图。参考图须实际存在且职责明确；未提供图时词自足，不假称已批。人形执行词出图前读[准确版式](../../references/execution-sheet.md)，先完整写画幅、上下占比、四格裁切和视觉主次，再写衣装细节，生成前只做轻量格式检查。未授权不生图；获授权用同一已展示正文，生成后直接交用户人工看，不默认自动审图、局部修补、复核或重跑。明确请求审图时才按准确版式看图，不自称图像通过。

普通任务可读真实旧工程作只读继承，不迁移、不覆盖active、不使旧批准失效；错误project_root报错。明确正式生产或旧typed调用才加载[工作流](../../references/workflow.md)、[阶段批准](../../references/phased-design.md)和[专项旧合同](../../references/specialist-contract.md)。旧complete、各pipeline及群演/非人继续兼容；模型推荐、程序通过和审图均不等于用户正式批准。

## Packaged references

- [references/final-asset-table.md](../../references/final-asset-table.md)
- [references/director-understanding.md](../../references/director-understanding.md)
- [references/prompt-document.md](../../references/prompt-document.md)
- [knowledge/index.md](../../knowledge/index.md)
- [skills/character-costume-designer/SKILL.md](../../skills/character-costume-designer/SKILL.md)
- [references/design-detail-standard.md](../../references/design-detail-standard.md)
- [references/execution-sheet.md](../../references/execution-sheet.md)
- [references/workflow.md](../../references/workflow.md)
- [references/phased-design.md](../../references/phased-design.md)
- [references/specialist-contract.md](../../references/specialist-contract.md)
