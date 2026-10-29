---
name: character-evidence
description: "核对剧本事实、资产表与场记来源并列冲突"
---

# 角色证据核对

读取 [证据规则](../../references/evidence.md) 和项目来源文件。以标准剧本原文为事实基准，资产表只供 ID/层级/状态索引，场记作可选镜头与情绪核对。逐条分类原文事实、保守推导、未批准提案、已批准选择；每条事实附 source_refs。事实冲突给出实际位置与影响；只有硬冲突或重大剧情设定才集中交用户决定，普通外观留白由设计者形成一个推荐。如受上游改版影响，列影响角色与全剧视觉基准是否需重审，只有明确正式登记才用CLI记录真实影响决议。普通提示词不前置逐外观证据台账，来源/版本由[文档工具](../../references/prompt-document.md)机械保留；生成后直接交用户，不自动审图/修补/重跑。

## Packaged references

- [references/evidence.md](../../references/evidence.md)
- [references/prompt-document.md](../../references/prompt-document.md)
