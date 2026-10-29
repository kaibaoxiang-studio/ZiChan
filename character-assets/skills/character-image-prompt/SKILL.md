---
name: character-image-prompt
description: "把具体角色设计保真编译为GPT Image 2.5提示词，默认同源文件与可读文档"
---

# 角色图像提示词

将当前具体设计编译成当前画幅可用的完整提示词，不临时发明脸、衣片或妆饰。先核成熟度：有可画结构就接续，缺哪处只回补哪处；candidate 仅改变批准状态，不免设计。没有工程可接真实冻结独立 delivery；错误工程不能自动降级。接口与真实命令见[提示词合同](../../references/prompt-detail-contract.md)。

先读[出图规则](../../references/prompting.md)与本次阶段相关规则。投影当前可见细节，按视觉主次整理为无部位标题的自然正文。允许同义、合句、去理由与重复；已选且入画的骨点、左右、比例、片数、叠压连接、色材分区、佩戴与状态不能静默丢改。主次只改排序和强调，不授权删小件；不入画内容留在设计。完成源细节到正文的语义核对；确定性检查不能冒充审美或看图。

默认后台交 `prompt-package.json`＋机械导出的 `提示词.txt`，TXT逐字等于 `prompts[].text`；同时把完整可复制正文机械合入同一份角色设计文档。用户只需该文档，版本和审计后台保留。只有本次明确只对话文字，才用 `delivery_mode:text` 免文件，仍交完整正文；不能模型自行把提示词请求改成讨论。

正式生产沿已批准设计、状态与图片锚点；task-local试改以冻结稿和只读正式父约束出候选，采用前不污染active。保留3:4头像、9:16全身、九宫格、模卡与四格／群像／非人对应布局，详见[阶段合同](../../references/phased-design.md)。本专项不调用生图；需要预览时由主控使用同一已展示正文，回图后实际审查。

## Packaged references

- [references/prompt-detail-contract.md](../../references/prompt-detail-contract.md)
- [references/prompting.md](../../references/prompting.md)
- [references/phased-design.md](../../references/phased-design.md)
