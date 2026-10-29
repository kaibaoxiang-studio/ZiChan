# 群演群像：逐状态单图执行资产

## 路线判定

正式工程先运行 `python scripts/character_project.py plan --project-root PROJECT`，读取每项的 `asset_mode`；独立文字请求按给定事实判断，不为此强建工程。新 phased 项目中，资产表层级为「群演／群像」且标准剧本结构化台词中有该资产名的指定发言，走 `speaking_extra`；无指定发言走 `ensemble`。两条路线**每状态都只产一张** `execution` 图片。若台词标为「某群名甲／乙」，正式生产先拆出有台词者的独立资产 ID。来源不足以判断发言时先核原文／结构化来源，不擅认无台词。已批准旧项目沿原路线读取，不自动迁移或作废。

两条群演路线都没有头像、九宫格、全身模卡、常规人物穿衣圣经及合成单人卡。人形 `speaking_extra` 的一张是独立 **9:16 四格执行图**；`ensemble` 的一张是同画布完整全身群像图。多个状态仍各有一张。若资产表只记一位无台词群演，则为单人 9:16 完整全身图。

有台词者先判真实形态：`SpeakingExtraDesignV1.morphology` 可为 human（省略时兼容旧默认）、humanoid 或 nonhuman。human/humanoid 用 9:16 四格；nonhuman 也只一张 9:16 执行图，但按获批 `execution_layout` 适配机器、动物等实际结构，不强加人脸、发型或无头服装格。所有路线仍先做当前具体设计，再交提示词；候选、批量和仅文字不豁免。

## 设计输入与职责

正式项目复用有效全剧 `ScriptContextV1`、获批 `ProjectVisualBibleV1` 与 `CastPlan`，核对媒介、时代、工艺、色域及近邻。独立请求按实际材料范围理解群体任务，不宣称已读全剧。群像设计师核原文动作、人数、道具、群体身份与状态；排位和差异化框架不代替脸、发、身体、衣装的设计方法。不得带入 DOCX 示例的卡通画风、虚构人物或排列习惯。

## 单图范围内的实际设计方法

**先选本组真正需要的方法，再设计，不为填字段补标签。** 有人形脸发、身体、衣装留白时，读取并采用 [脸部](../skills/character-face-design/SKILL.md)、[发型](../skills/character-hair-design/SKILL.md)、[形体](../skills/character-body-design/SKILL.md)、[款式](../skills/character-costume-style-design/SKILL.md)、[剪裁](../skills/character-costume-cut-design/SKILL.md)、[材质](../skills/character-costume-material-design/SKILL.md)中的相关方法；按具体缺口取其知识。方法在本组读一次并复用，成熟部分继承，不逐人重读、不为每人新建全套专项会话。颜色、妆饰、特殊身体只在当前任务需要时增加对应方法。纯非人组改用[形态与结构](costume-and-morphology.md)的适用逻辑，不强读无关人类五官／衣装规则。

1. **全组共同基准先具体设计一次。** 从叙事功能、世界工艺、动作与维护形成共享视觉语言。有共用衣装时，确定主衣／衣层、整体廓形，前后片与领肩袖如何接合，开合／固定、下摆及活动余量，材料厚薄、垂坠、反射和实际色块位置。标记在前后何处出现也要接得上；“同款耐磨制服、相同反光条”不是连接方案。共享结构写入 `shared_visual_grammar`，成员继承它并说明放量、穿法或局部差异，不需把整段基准复制多份。不同构造不为了同组语言强套同一件衣服。
2. **每个成员的差异落到结构组合。** 在本画幅可读范围，脸型名称之后给额／颧／颌／颏的连接、眉眼与鼻口的形状和相对落点；发型名称之后给发际／分缝及人物左右、前侧后体积、长度和收束。身体给胸盆体块、肩胯／肢段关系、重心及动作中的连接，衣装给共同结构下此人的松紧、开合、卷袖／下摆、受力褶等真实穿法。长脸、短发、窄肩、开襟等分类词要继续具体化，不能以换姓名或几句形容词充当不同的人。以组合而非每个部位都夸张建立差异；不增加疤痕、新身世或不入画的微纹理。群像不要求每人制作单人卡、五组比例表或逐五官审计表。
3. **非人结构单独解决。** 从来源锁定部件数量与形态，确定主体体块、关节／附着、承重与移动、前侧背连续、接口开合和表面分区；动作接在同一结构上。混合组的人形衣装与非人壳体分别用合适材料物理，不能给机器贴织物纹理或补人脸毛发。未见图不宣称运动学／接地视觉测试通过。
4. **把结构放进一次连贯排位。** 明确人数照数，未明确时才以 `representative_choice` 标代表人数。按人数和动作选横向画幅，多人宽大于高，单人9:16，没有固定21:9。逐槽位写位置、体块姿态、脸发或非人结构、衣装／色材、动作和道具所有者，固定从左至右顺序，全身与脚部完整不互遮；世界、身份、信仰或阵营的新设定单列。数量与物件正确不等于设计已完成。

总控交付前核对：共享衣装能否由文字接成前侧背同一件；各成员能否从轮廓体块、脸发结构与动作读出实质差异；动作与穿法是否相容、物件是否归对人；非人部件是否连接合理。缺哪处只补哪处，不重新扩大成每人全套生产。后台保留实际采用的必要方法及其具体成果，不新增每成员的会诊证明或字数下限。完整设计、修改结果及当前提示词维护在同一份人用角色设计文档，图片另存。

用户给的《AI角色_上传一个故事做出整套角色设计.docx》只提供**整组全身人物在一张画布上编排**的形式参照。获批项目风格优先于该文档示例的画法、色彩和故事内容。

## 记录和图像合同

以下为当前**正式** `extra-design`／`ensemble-design` 生产入口。该入口仍执行原字段逐字覆盖；不能因为全局引入 `fidelity_review` 就宣称这里已跳过旧规则。独立冻结候选的来源与保真接口另见[提示词合同](prompt-detail-contract.md)，不自动迁移本节正式分支或改动旧批准。

### 有指定台词：`speaking_extra`

先建并批准 `SpeakingExtraDesignV1`：`character_id,variant_id,parent_refs` 指向 `script-context,visual-bible,cast-plan` 的当前 SHA；`narrative_function,spoken_line,world_style_translation,face_and_hair,body_and_posture,costume_front,costume_back,color_and_material,prop_and_action,source_refs,evidence_status,new_lore_policy,unresolved`。`spoken_line` 必须出自该人物原文台词，`source_refs` 至少对应一条台词；外观留白按项目美术基准主动设计，身份或剧情新设定另审。

上述脸发与服装前背字段用于 human/humanoid。nonhuman 用非空 `morphology_details` 对象逐项写本形态的身份结构、前后/侧面连接、表面与附着等可见设计（各值为具象文字），保留体态、色材与道具动作共用字段；另写非空 `execution_layout`，其中 `description` 用可直接入提示词的文字说明一张 9:16 画布如何展示实际形态，其他格位字段可按本形态组织。不要为凑人类字段给动物加衣服或给机器加头发。

人形获批后仅提交 `stage:execution` 的 `CharacterPromptPackageV1`：`morphology:human|humanoid`，`aspect_ratio:9:16`，`anchor_images:{}`，`design_basis.records` 只绑定 `extra-design:角色ID:状态ID` 当前 SHA。`layout` 用正脸、约 45° 半侧脸、放大无头正面服装、完整背面四格，提示词写出批准的造型与项目风格；台词作为表演语境和设计依据，不作为图内文字。实际审图与批准一次，打包 `CharacterSpeakingExtraPackV1`；不要求先生成三张身份图。

human/humanoid 的提示词分别继承同一 morphology 和上述四格；nonhuman 的 morphology 与 `layout` 必须等于已批准设计，正文与验收项承接 `execution_layout.description`。新提示词每条都须逐字保留已选的脸发/体态/服装前背/色材/道具动作字段；非人改为体态/色材/道具动作和每项 morphology_details，不能把它们缩成“普通制服”“一只动物”。验收项同时包含这些具体设计文字，逐项核图；旧已批准提示词保留原读取/打包合同，不因新覆盖检查自动失效。

```sh
python scripts/character_project.py submit --project-root PROJECT --kind extra-design --character-id CHR --variant-id STATE --file extra-design.json
python scripts/character_project.py approve-record --project-root PROJECT --kind extra-design --character-id CHR --variant-id STATE --operator OPERATOR
```

### 无指定台词：`ensemble`

提交 `GroupEnsembleDesignV1`：`character_id,variant_id,parent_refs` 精确引用已记录的 `script-context,visual-bible,cast-plan` SHA；`narrative_function,world_style_translation,shared_visual_grammar,variation_logic,quantity_basis,quantity_status,script_count,member_count,source_refs,arrangement,members[],new_lore_policy,unresolved`。`members` 数与画中人数一致，每项含唯一 `slot`，以及 `body_and_posture,face_and_hair,costume_structure,color_and_material,action_or_prop,evidence_status`。批准当前设计后才写正式提示词。

```sh
python scripts/character_project.py submit --project-root PROJECT --kind ensemble-design --character-id CHR --variant-id STATE --file group-design.json
python scripts/character_project.py approve-record --project-root PROJECT --kind ensemble-design --character-id CHR --variant-id STATE --operator OPERATOR
python scripts/character_project.py submit --project-root PROJECT --kind prompt-package --character-id CHR --variant-id STATE --stage execution --file group-prompt.json
```

提示词包为 `CharacterPromptPackageV1`，`morphology:group`，`stage:execution`，`anchor_images:{}`，`design_basis.records` 只绑定当前已批准群像设计键和 SHA。`layout` 为 `ensemble_lineup`，`single_canvas:true,full_body:true,member_count` 与 `ordered_slots`；写每人准确的槽位、衣装和道具，提示词及验收项明确画幅、人数、全身、顺序与项目风格。不得出现四格布局。回图后实际核画中人数、完整脚部、轮廓差异、道具所有者、项目风格与画幅；审查和用户批准各一次，再 `package` 为 `CharacterEnsemblePackV1`。代码门槛校验来源、批准、SHA、图像和打包；图像审美仍须人工看图。

新群像提示词每条及其验收项都保留各槽位的 body_and_posture、face_and_hair、costume_structure、color_and_material、action_or_prop 具体文字，项目风格也须出现在每条正文，不能只在某条备选里出现。数量从本资产名/别名对应的原文局部核对；名字含“三个”等明确数量或目录后缀“群像/群演”时仍核原文，不将同段其他道具数量当人数。跨证据出现冲突时阻断待核，不猜代表人数覆盖明确事实。

## 来源边界

原始教学文档：`AI角色_上传一个故事做出整套角色设计.docx（来源文档名；不作为运行文件依赖）`，SHA-256 `d42c3893aa8399f81f28c8fd16a95e74cf485960649f4aff15f08c629053dc94`。仅采纳单画布群像编排、完整人物、顺序和群内差异的方法；原图画风、21:9 画幅与示例故事不作为默认规则。
