# v0.2.6 验收记录

## 范围与依据

- 宋也 S03：复用测试 1 的标准化剧本、已有人物方向稿及旧版 `宋也-S01-S05服饰设计提案.md`。原文确定洁白婚纱和婚礼剧情；旧稿为常规小方领、短袖、A 字裙的文字方案，旧服饰预览为横向图。新版仅形成未批准文字设计草案，不写回用户正式资产项目。完整剧本 SHA-256：`3aac648fc06e820fbaddcd4ed28fe66a07108f65fc8340af86973d97b87f2435`；方向稿 SHA-256：`cea5b648474f0bb218e596534158e68f2fce3a484d2978d89233b126418e6b6f`；旧稿 SHA-256：`1a937033da97223aff5d9c4fcbe5a28cf71bc32f2efc1afb34e37d1d38231e4a`。
- 普通角色：新建虚构短剧，前台值班员陈榆递笔、扶导引牌、搬备用座椅和送水。用于检查 `tier:compact` 仍有具体剪裁与行动逻辑，不代表用户剧本。
- 调用经 `character-assets/harness.py run-capability --capability character-costume-designer` 真正执行新 Skill。Harness dispatcher 使用 v0.2.5.1 的 `ephemeral:true` 临时会话；运行目录在仓库忽略的 `.harness/v026-acceptance/`，不会生成持久聊天。首轮宋也完整剧本调用因 600 秒上限超时；随后改为同一剧本的逐行摘录，加已有人物总控全文方向稿，不伪称服饰设计师重新读完全文。普通角色第一次相对路径未被输入哈希收录，取消后改绝对路径重跑；只采用可追溯的重跑结果。

## 结构回归

本机 Python 3.12：`python -m unittest discover -s creator-src/tests -p 'test_*.py'`，**48 项通过**。覆盖旧项目读取、v2 phased/complete 显式迁移保留获批身份图及拒绝已批准旧服饰图、v3 四图链路、逐状态 9:16 四格提示词合同、风格圣经与服饰快照版本绑定、逐状态局部失效、圣经变更全部状态重审、V3 打包，以及临时会话隔离。结构测试使用合成图片字节验证状态机，不声称视觉质量。

`harness.py doctor`：21 项能力、21 个 Skill，结构有效。安装包 `dist/character-assets-0.2.6.zip` 经 `harness.py package` 校验为 valid；SHA-256：`09e8051bfb7d8eefe053ff73da07e8e46f983bde1fbcecd004850cf4aba01a5c`，142 个文件、无重名、无原始 DOCX 或 ZIP，内含新服饰设计师与三份新知识快照。本机通过 `codex plugin add character-assets@zichan-local --json` 安装到 `~/.codex/plugins/cache/zichan-local/character-assets/0.2.6`，关键文件哈希与仓库构建物一致。没有为发布生成新图片；新图审美由用户测试正式版。

## 真实 Skill 文字验收

**普通角色陈榆：通过。** 用 `run-capability --capability character-costume-designer` 真实调用，run ID `run-d1709f48dc284c49`，默认模型设置、425 秒完成；输入短剧 SHA-256 `cc4517013cb5f4345234a041956c294d370ee5bb8f0847f710a8ff727757dcaa`。产出[文字设计](ordinary-design.md)及独立 `CostumeStyleBibleV1`、`CharacterStageDesignV1` 草案，三文件均由 Harness 记录 SHA。简版并未退化为“酒店制服”：短方摆马甲、背中暗箱褶、腋下插片、裤前浅褶、前背缝接、部位配色和材料厚度都对应递笔/搬椅/送水动作；饰品有具体不使用理由。输出明确没有正式项目、批准或实图验证。

**宋也 S03：文字验收通过。** 最终采用同一剧本的带行号摘录、既有全文方向稿与旧版 S03 提案运行 `character-costume-designer`，run ID `run-0b1a8ed8930f4ee6`，状态 `completed/succeeded`；2026-10-23 03:47:18–03:54:20 UTC，约 421 秒。最终 `design.md` SHA-256：`4e46ecb8dd6c4a6e7b0680ebcb75fa588c91bb44ca73838639eda9946b5ba571`，保存在仓库忽略的 `.harness/v026-acceptance/songye-concise/.harness/run-0b1a8ed8930f4ee6/character-costume-designer/attempt-1/design.md`。输入摘录 SHA-256：`51a13e1e43dc8a6498e40f2788b46e9f7ad262182d73f16c88a10ecde863301e`；方向稿与完整剧本来源哈希见上文。此运行复用总控全文理解，没有把摘录冒称为服饰设计师阅读全文。

| 检查点 | 旧 S03 提案／预览 | v0.2.6 实际文字结果 |
| --- | --- | --- |
| 人物弧线 | 常规小方领、轻收腰、A 字婚纱，没有解释她为何这样穿 | 以“过去被隐匿、如今以自己的名字公开被尊重”为穿衣命题；自然肩、可活动、前幅平净而后侧轻展，保留温柔与行动空间 |
| 剪裁与前后连接 | 两片主裁片和浅褶，侧背接缝、褶根与开合未明确 | 七片上身与七片裙身在腰缝对位，后侧内倒褶、后中拉链＋暗钩、领袖贴边和软腰贴均有位置与作用 |
| 动作与材质 | “不紧勒”“绉缎＋薄纱”缺少活动与重力验收 | 抬手擦泪、十指交握作为试穿动作；袖山、腋下活动片、胸腰松量和各衣层克重、下摆分离与回落方式具体可核对 |
| 专项与妆造 | 服饰类别和附属物清单居多 | 款式、剪裁、配色、材质分别落到衣服部位；饰品解释为何不增，婚礼妆面和发饰只改变施加层，不改变身份脸 |
| 图像链路 | 旧预览 1536×1024 横图，容易压短全身比例 | 新项目合同限定每状态一张 9:16 竖版四格执行图；本次按计划只验文字，不声称已经验证新图审美 |

最终稿仍是**未批准的设计草案**，未写入用户项目、未生成图片。耗时记录显示真实调用的创作质量有改善，但约七分钟的单状态成本仍偏高；本版通过复用总控全文理解和聚焦相关场次控制重复阅读，未把这次运行包装成快速响应。此前两次宋也较宽任务在 600 秒限时内均未完整返回，其中第二次已形成实质设计文件；最终验收只采用完整成功的精简调用。
