# 群演群像：逐状态单图执行资产

## 路线判定

先运行 `python scripts/character_project.py plan --project-root PROJECT`，读取每项的 `asset_mode`。新 phased 项目中，资产表层级为「群演／群像」且标准剧本结构化台词中有该资产名的指定发言，走 `speaking_extra`；无指定发言走 `ensemble`。两条路线**每状态都只产一张** `execution` 图片。若台词标为「某群名甲／乙」，先拆出有台词者的独立资产 ID。来源不足以判断发言时先补结构化剧本，不能默认为无台词。已批准旧项目沿原路线读取，不自动迁移或作废。

两条群演路线都没有头像、九宫格、全身模卡、常规人物穿衣圣经及合成单人卡。人形 `speaking_extra` 的一张是独立 **9:16 四格执行图**；`ensemble` 的一张是同画布完整全身群像图。多个状态仍各有一张。若资产表只记一位无台词群演，则为单人 9:16 完整全身图。

有台词者先判真实形态：`SpeakingExtraDesignV1.morphology` 可为 human（省略时兼容旧默认）、humanoid 或 nonhuman。human/humanoid 用 9:16 四格；nonhuman 也只一张 9:16 执行图，但按获批 `execution_layout` 适配机器、动物等实际结构，不强加人脸、发型或无头服装格。所有路线仍先做当前具体设计，再交提示词；候选、批量和仅文字不豁免。

## 设计输入与职责

人物总控提供全剧 `ScriptContextV1`，`ProjectVisualBibleV1` 提供**获批**的项目媒介、真实度、时代、色域、材质与光线，`CastPlan` 提供同组和邻组差异。群像设计师核对原文动作、人数、道具、群体身份与状态，实际执行相关服装、体型、发型、脸部与材质规范；只加载当前问题所需知识。不得把 DOCX 示例中的卡通画风、虚构人物、比例或排列习惯带入项目。

1. 确定叙事功能和全组共有的视觉语法：例如同一机构的制式可以共享肩线与材料，个体仍可有不同身形、穿着磨损和站姿。具体差异要服务场面，不因群演身份全员同脸，也不为差异捏造疤痕或新身世。
2. 剧本明确「三名」就画三名，列出每人的左右槽位与实际道具。人数未写明时选能在单画布保持全身可辨的代表人数，把它标为 `representative_choice`；不能写成剧本人数。可根据人数与动作选择 16:9、2:1 等横向画幅，没有固定 21:9；多人必须宽大于高。单人固定 9:16。
3. 逐人写可画的体型与重心、脸发块面、服装廓形与连接、颜色材质、手中道具/动作，说明哪些是原文事实、推导或创作选择。共性和个体差异都要在一张缩略图上能看见。道具不漂移、不在两个人之间混属。
4. 只建议一套连贯排位：从左到右固定顺序，脚底位于同一合理地面，人物完整不互遮；场景背景遵守项目批准记录。世界、身份、信仰或阵营的新设定必须列为未决，不能用装饰伪造。

用户给的《AI角色_上传一个故事做出整套角色设计.docx》只提供**整组全身人物在一张画布上编排**的形式参照。获批项目风格优先于该文档示例的画法、色彩和故事内容。

## 记录和图像合同

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

原始教学文档：`/Users/chenhaojia/Documents/ChatGPT/资产标准化输出物/AI角色_上传一个故事做出整套角色设计.docx`，SHA-256 `d42c3893aa8399f81f28c8fd16a95e74cf485960649f4aff15f08c629053dc94`。仅采纳单画布群像编排、完整人物、顺序和群内差异的方法；原图画风、21:9 画幅与示例故事不作为默认规则。
