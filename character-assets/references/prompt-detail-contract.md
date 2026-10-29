# 提示词交付与设计保真 v0.2.16

先有当前范围的具体设计，再编译提示词。定位／职业标签不是设计；候选不免结构。成熟provided稿可直接核对编译，不追补虚假专项收据；缺哪处只补哪处，不重新采访方向。

## 人用一份文档，机器保持同源

提示词默认后台保存完整 `CharacterPromptPackageV1` JSON与机械导出UTF-8 TXT；TXT精确等于 `prompts[].text` 按顺序以两个换行连接，末尾一个换行。对话展示、角色设计文档当前prompt段和实际生图正文都取同一正文。默认不要把JSON／TXT／收据等中间文件堆展示给用户；用户只用一份持续更新的角色设计文档，图片单独。

```sh
python scripts/export_prompt_text.py /internal/prompt-package.json --output /internal/提示词.txt
python scripts/verify_design_delivery.py document --design /internal/design-result.json --prompt /internal/prompt-package.json --output /delivery/角色设计.md
```

局部改稿更新已有完整人用文档时，`document` 用可重复的 `--base-design /internal/既有完整设计.json` 继承未改域，再用当前design覆盖实际改动；没有base不允许把旧完整文档覆盖成只剩局部稿。正式stage记录也可作真实base；候选清楚标未替正式。

只有用户本次明确只要对话文字，真实task用 `delivery_mode:text` 才省文件；仍交完整可复制词。模型不能自行把files或prompt交付改成discussion。Harness文件路径固定可留内部；实际成功须有本次完整成果，不能假路径或空摘要。

## 当前可见设计投影

先确定画幅、状态、参考职责和实际可见范围；取当前已选结构，区分主锚点与次要完整细节。头像不塞鞋背面，正面身份连续性不等于再画第二视角。实际入画的小件不能为省字标不可见；若真的无法承载，指出具体冲突并回设计局部调整，已批结构改变按原规则。

独立文生图、或没有提供旧图作为实际编辑参照的最终正文，应直接描述当前画面，不带未提供的“首稿／旧稿”参照、before→after或已被替换的旧数值。若上游当前可见字段或专项结果混入历史，先依[当前状态与修改历史分离](director-understanding.md)整理真实来源，再冻结／提取保真约束：当前字段只留现状，历史留修改说明。不能让旧值因硬标记被强迫写进正文，也不能为避检查改掉当前设计。当前发长可以写现值，轮廓写已选形状和连接；历史位移不转成虚构的绝对发际位置。当前脸长相对颧宽、骨点关系、头身等形态比例仍然保留，这条不禁止有明确端点的相对描述。用户明确提供待编辑参考图时，局部编辑指令可以对那张真实图说明相对变化及保持项，须指明图的职责，不与无参照的文生图混用。原始结果与整理依据保留，不改变设计选择的整理无需额外审批。

主控将用户实际指定画幅解析为task的`aspect_ratio`，再核包字段与真正的画幅正文，不能让默认3:4覆盖明确1:1。未填时程序仅识别很窄的肯定画幅语句；否定、多选和其他歧义由主控结合原话解析，不猜成默认。身体头身、肩髋或肢段的比例不是画布比例。

编译允许同义、合句、去设计理由和重复，调整顺序与强调强度；不允许静默删改人物左右、数值／比例、衣片数量形状、叠压连接、色材分区、佩戴及状态起止。主次不是删结构许可。“三片叠压衣片”不能压成“层次丰富”，“左耳一枚耳钉”不能压成“精致饰品”。不定通用字数或案例密度下限。

## 来源分支

正式项目沿 `design_basis`／`anchor_images` 的真实当前批准依据和preview例外；旧无新标记包继续原合同。独立设计或已批试改可采用 `purpose:candidate` 与 `design_source.kind:task_frozen_delivery`，来源为实际冻结delivery和真实输入文件：`path,sha256,inputs_path,inputs_sha256`。task与package的来源须相同。可选正式 `project_root,parent_refs` 约束在冻结inputs中只读校验；候选不继承批准、不写active ledger。错误project_root不能降独立模式。

冻结命令见[专项交付](specialist-contract.md)。文件实际存在才计算字节SHA；明确纯text则用真实本轮稿／消息定位，不能虚报文件哈希。

本次明确不落任何文件的独立文字候选，可用`delivery_mode:text,purpose:candidate`和`design_source{kind:task_text_design,text,source_ref}`传实际完整当前设计原文与真实稿／消息定位。可选`text_sha256`只核实际UTF-8内存hash；主控确需检查当前可见硬约束时可传`preserve[]`，每项须真在原文，不让用户逐句填表。此分支不创建JSON、TXT或冻结文件，也不能声称核实消息真实性、设计成熟度或完整语义；主控仍须实际检查已选可见结构和设计质量。不能用于files、正式项目／资产ID／批准或正式下游锚点；正式生产仍按真实登记接口办理。

## 结构保真与核查

显式新编译可用 `fidelity_review:PromptFidelityReviewV1`，由 `scripts/prompt_fidelity.py` 从真实源设计机械列举当前inventory，核完整覆盖、实际正文片段、源与prompt版本及明确数值／左右／数量／状态；主控仍须真实核语义和结构。不把映射给用户先填，不另增必经审计岗位。

review含 `source_sha256`、`prompt_sha256`（prompts的content_hash）、`semantic_review{reviewer:controller,verdict:pass,unresolved:[],notes}` 与 `coverage[{prompt_id,detail_id,span}]`。源细节若已逐字完整出现在正文，程序自动核覆盖，不必再手填同文mapping；只有真实同义或合句无法字面确认的改写才需coverage映射，完整inventory和全局semantic_review仍保留。notes写本次实际核对发现，span是真实正文片段；ID齐全不能证明语义等价，代码明确不作这种承诺。无法确认时保守留原表达或提出具体冲突，不能用通过的表格隐藏遗漏。

正式新阶段仍保存真实可解析的专项采用与 `payload.prompt_detail_contract`。未选新保真编译的旧合同继续逐cue字面核对，历史批准不自动失效；不能省review却宣称已用同义保真分支。固定cue种类是机器合同维度，不是让所有人长相或饰品一样。

## 图像边界

保留头像3:4、全身9:16、九宫格、模卡及人形执行图四格；群演与非人按各自布局。参考图只控制指定维度，中性背景不暗加场景。未授权不生图；获授权预览使用同一完整正文。回图实际打开核身份、比例、结构、佩戴、格位与背景，程序通过不代表画出来。案例只示范方法与状态分离，不是全员密度／风格模板。
