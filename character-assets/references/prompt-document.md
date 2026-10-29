# 普通角色：提示词就是设计稿

默认一个整合推荐方向，深度设计直接体现在可复制提示词里。每角色一份持续Markdown文档，四类为avatar、expression、full_body、execution，execution按实际状态追加。当前只要一阶段或局部就完成该范围，不为齐四类扩大委托；完整四类委托则交齐，不能缩成头像。群演单图与非人走实际分支，不机械凑四类。

## 直接设计与一次核对

先理解或复用人物、世界、近邻与已选约束，按问题使用相关专项方法。常规inline；跨域结构冲突、复杂形体工艺或同一问题反复失败才独立会诊。模型形成一套推荐，不逐参数问、不造A/B/C；硬冲突、重大剧情新增或改变已批身份才集中提出。改稿自然产生同一方向的新版本。

脸发写骨点、五官形状落点连接、发际分缝、体积发流与固定。完整身体写同一测量姿态/端点下头身、肩胯、躯腿、肘腕、膝踝五组关系和体块重心；数字不是画布比例。衣装写主衣廓形、衣层、重点衣片数量形状、叠压/缝接/闭合/固定、前后接续、动作余量与色材。仅当前需要的结构进入本阶段词，“清秀、干练、真实”不能代替这些决定。

不前置长设计稿、完整typed design、body_form对象、逐专项rules/results/知识SHA、十三项计划、cue映射或freeze。方法须真实运用，但不另写“问题→方法→成果→采用位置”证明。用户要解释、真实独立会诊或明确旧正式合同需要时才留实际返回，不回填历史执行。

每条词只描述当前画面与当前值，完整自足，不以“同上”代替必要结构。理由、弃选、旧数值、方法名、审批/审计话语不塞正文。未入本阶段画面的结构放在适用阶段词里，不另建完整设计台账。需要时只简短说明“除已引述剧本硬约束外，新增外观为设计选择”；真正影响剧情的事实保留实际原文定位，无需每个眉眼填写证据标签。

完成后一次核对：硬要求、结构连接与动作、当前状态、视觉主次、跨四类身份/体型/衣装连续性。成熟稿只补真实缺项；局部读最新版文档及相关原文，只改受影响条目，未改决定不重设计。

## 同一文档与后台工具

每轮读当前文档/后台context，不从聊天全文重拼人物。模型只写本次update。Runtime在运行前机械提供本任务真实task-inputs.json路径，含request、sources真实路径数组、所需阶段/状态和已解析画幅；不让用户填内部问卷，不让模型重复编真实inputs或hash/父引用/批准。

内部路由字段delivery_contract使用prompt_document；明确旧scope、formal目的或typed来源走legacy_typed，不能静默降级。这是实现路由，不是用户要选的新模式。普通新稿的project_root及parent_refs可只作只读继承依据，不因此升级为正式生产。

内部CLI：

```sh
python scripts/prompt_document.py context --document /delivery/苏老太_角色提示词.md
python scripts/prompt_document.py save --update /internal/prompt-update.json --inputs /runtime/task-inputs.json --document /delivery/苏老太_角色提示词.md
```

有实际旧工程需继承时，context可加--project-root /actual/project --character-id 实际ID，只读合法记录/批准。错误工程报错，不降独立；不迁移重建旧工程。实际参数以本版CLI为准，验证状态见VALIDATION，不将接口约定当实测通过。

Update最小结构：

```json
{
  "schema_version": "CharacterPromptDocumentUpdateV1",
  "subject": {"name": "当前人物", "local_key": "local-character"},
  "entries": [{"stage": "avatar", "state_id": "base", "text": "本阶段完整可复制提示词"}]
}
```

这是封装示意，示意text不能当成品。stage取当前委托四类，execution用实际状态；aspect_ratio可省用阶段默认，用户明确画幅从真实inputs承接。更新已有文档时携context返回的expected_revision。可选references:[{path,role}]只列实际图与具体职责；constraints:[{text,source_ref}]只承接真实约束。未提供图时词自足，不造文件或approved/approval/anchors。

工具按(stage,state_id)合并，同key只有一个当前方向，未更新词原文保留；同内容重跑不造历史。读取真实来源/参考并自动算SHA，维护文档旁隐藏目录.<文档名去扩展名>.character-assets/中的current.json、同源提示词.txt和实际变更history。Runtime依据验证返回登记旁文件，不让模型手列后台清单；用户只需文档。外改或并发revision冲突受控拒绝，不覆盖他人新稿。

## 图片与正式边界

候选词不等待上游正式图。人形默认头像3:4、表情九宫格、全身9:16中性模卡、各状态9:16执行图；后者先完整写[布局、裁切与视觉主次](execution-sheet.md)，再写衣装细节，不能仅metadata声称通过。真实用户画幅覆盖、群像人数、非人布局按任务处理。

未授权不生图；获授权用同一已展示正文，生成前仅轻量提示词格式检查。生成后直接交给用户人工看，默认不自动审图、局部修补、复核或重跑。用户明确请求审图时才按[审图方法](review.md)实际查看；明确请求修改才编辑。不自称图像通过或代用户批准。

模型推荐不等于用户批准。普通试改只读旧工程，不写active、不撤销旧批准；明确正式采用/打包或旧typed输入才按[工作流](workflow.md)、[专项旧合同](specialist-contract.md)、[阶段批准](phased-design.md)登记实际版本和真实确认，不回填不存在的历史收据。
