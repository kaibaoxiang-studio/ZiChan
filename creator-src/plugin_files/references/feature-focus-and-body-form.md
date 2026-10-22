# v0.2.2 焦点与三维形体交接

本规则服务于写实或其他已批准的项目美学。课程中的“2–3 个焦点”“剪影为王”是审阅启发，不是机械配额。剧本事实、已批准决定及角色行动优先。不要把五官、体型、伤痕直接映射成品格，也不要默认美型、疤痕、痣、夸张长腿。

## 先路由，再委托

逐人设计前在项目 `drafts/specialists/` 写 `CharacterSpecialistRouteV1` JSON：`character_id`、`variant_id`、`specialists{专项ID:{decision:invoke|skip,trigger,reason}}`，覆盖 11 项。`trigger` 指出检查的是何种具体缺口或已充分的已批内容；`reason` 写路由决定及依据。特征焦点由 `$character-feature-focus` 负责，身体比例、颅胸盆体块与动作由 `$character-body-design` 负责，群像总控仍负责近邻横向比较。真正需要的专项必须实际调用，保存返回的 `CharacterSpecialistProposalV1.1` JSON；不要通过写一句“已调用”模拟执行。没缺口的专项可以 `skip`，理由需具体。

主控将每份 used 提案复制到项目 `drafts/specialists/`，保持 JSON 原样并计算 SHA-256。操作者在本轮选择方案后，在设计卡 `specialist_coverage[ID]` 中记录 `proposal_ref`、`proposal_sha256`、`selected_option_id`、`applied_fields[]` 和 `applied_elements[{field,element_index}]`。`element_index` 是被选方案 `design_elements` 的零基下标。字段文本须忠实体现该元素；脚本只验证真实文件、哈希、目标、选项及字段映射，语义采纳由主控与操作者审阅。`not_needed` 要与路由中的 `skip` 一致。

## V2.2 设计卡

新重点人形卡沿用 V2.1 的六组细节，新增：

- `feature_focus{core_sentence,primary_anchors[],quiet_features[],imperfection_policy,view_checks}`。锚点写 `part,geometry,basis,visible_views[]`；若不是 2–3 个，写 `anchor_count_rationale`。安静区写 `part,decision`；不必故意让它丑。`imperfection_policy{status:none|existing|operator_approved,detail,basis}` 可明确选择不加新瑕疵。`view_checks` 分 `silhouette` 和 `occlusion`，各写 `status:passed|failed|not_tested,evidence`；未实际看图时保持 `not_tested`。
- `body_form{proportions,masses,views,action_check}`。比例写躯干/腿、臂段、腿段的**相对关系**；体块写头、胸腔、盆腔及连接；正侧背各写同一骨架的可复现形态；动作写站姿、剧本动作、活动能力判断与检查状态。尚无图像或关键姿态时状态为 `not_tested`。
- `route_ref` 和 `route_sha256` 指向路由 JSON。十一项 `specialist_coverage` 中 used 项均要完整提案交接。`submit`、`approve-record` 和后续批准卡读取都会校验外部文件哈希，防止提案被悄悄替换。

若用户只提供头像需求，仍要有身体设计的最小稳定结构供后续全身资产衔接，但不要在头像提示词里硬塞不可见的腿、背面信息。非人角色按形态沿用 V2 路线，不能强制套人体比例。
