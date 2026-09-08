# Codex 操作手册 — 项目 1：全屋定制拆 BOM 脚本

> 用途：指导用 Codex CLI 完成项目 1 全部开发任务（Day 4 基础版 8 模块 → Day 5 收尾 → Day 6 升级包）
> 分工说明：本文件由 Claude Code 提供**任务序列 + 每步给 Codex 的指令 + 验收动作**；标 🔧 的区块是 Codex 具体操作细节（启动方式/审批模式/上下文管理等），**由你按 Codex 教程知识库补充**——补充完的版本即为《Codex 落地使用手册》项目 1 篇的素材
> 关联文档：本目录 `rules.md`（喂给 Codex 的业务规则上下文，须为人工消化版）、`CLAUDE.md`（各模块验收标准）、《项目实操手册-艾迪尔4大项目-new.md》

---

## 0. 开工前状态检查

- [ ] Codex CLI 已安装并配置 API Key，`codex --version` 能出版本号
- [ ] `rules.md` 已完成人工消化改写（⚠️ 不能直接喂 AI 初稿——Day 3 验收红线）
- [ ] `data/orders.xlsx`（50 行，含 2 条埋雷）与 `data/prices.xlsx` 已就位
- [ ] 工作目录：在 `项目1-全屋定制拆BOM脚本/` 内启动 Codex（便于它读取本地文件）
- [ ] 🔧 待补：Codex 启动方式、审批模式选择建议（如 suggest / auto-edit / full-auto 的取舍）、会话恢复方法

## 1. 通用工作纪律（贯穿全部会话）

1. **一次只做一个模块**：新开会话或明确说"只做 X"，验收通过再下一个
2. **上下文先给全**：每条指令带上 rules.md 对应章节，不让它猜业务
3. **每个模块都要求附 pytest 测试 + 运行验证方法**
4. **幻觉抽查**：Codex 引用的库函数/参数要对照官方文档验证存在；数值结果抽样对照 rules.md 第 5 节手算基准
5. **卡点纪律**：单模块卡超 2 小时 → 立刻简化模型（任务书 Day 4 预警：讲清楚简化合理性 > 堆功能）
6. 🔧 待补：如何让 Codex 读本地文件（rules.md / orders.xlsx 列结构）；如何审查它给的 diff；如何执行并反馈验证结果

---

## 2. 会话 0：Kickoff（项目上下文注入）

**目标**：让 Codex 建立项目全貌认知，理解 8 模块顺序与分工纪律。

**给 Codex 的指令**（手册 Kickoff 原文）：

> 我要开发一个"全屋定制订单自动拆 BOM"的演示项目，Python 实现。业务规则见 rules.md（我会贴给你），数据结构见下。请按以下顺序工作，每次只做一个模块，写完给我运行验证方法：
> 1. parser.py：读取 data/orders.xlsx，校验必填字段与数值合法性（尺寸>0），返回订单对象列表
> 2. bom_engine.py：按拆解规则把每个柜体订单拆成部件清单（部件名、数量、长×宽、板材）
> 3. hardware_calc.py：按五金规则计算五金清单
> 4. optimizer.py：汇总板材面积×1.08 损耗，计算标准板材张数
> 5. validator.py：校验工艺约束（部件长度≤2400、宽度≤1200），违规订单进 reject 清单
> 6. report.py：合规订单输出采购清单 Excel（含板材料号/数量/五金明细/成本合计），reject 订单输出原因
> 7. db.py：采购清单写入 SQLite，提供统计查询：本月板材用量 Top5、单均五金成本、拦截订单统计
> 8. main.py：CLI 串起来，`--input data/orders.xlsx --outdir output/`
> 每个模块附 pytest 测试。先从 parser.py 开始。

**预期产出**：理解确认或澄清提问，不动手写代码之外的模块。
**验收**：它复述的模块顺序与上面 8 步一致；没有自行发明规则。
🔧 待补：rules.md 大段内容的贴入方式（直接粘贴 vs 让它读本地文件）。

---

## 3. 会话 1–8：基础版 8 模块（每模块一节，格式：指令 → 产出 → 验收 → 幻觉抽查点）

### 3.1 parser.py

**指令**：
> 写 src/parser.py：用 pandas 读取 data/orders.xlsx，校验必填字段（order_id/customer/cabinet_type/width_mm/depth_mm/height_mm/board_material/door_count/drawer_count/shelf_count/hinge_spec）齐全、尺寸字段为正整数；任一行违规即报错并指出行号与字段名。订单用 dataclass 返回列表。附 pytest：正常解析、缺字段、负数三组用例。

**验收**（CLAUDE.md）：50 行全解析；空值/负数报错且报错信息含行号。
**幻觉抽查点**：pandas 读 Excel 的参数名；dataclass 字段与 xlsx 列名一致性。

### 3.2 bom_engine.py

**指令**：
> 继续。parser.py 已验收通过（50 行全部正确解析，2 条埋雷订单数据结构正确）。现在写 src/bom_engine.py，拆解规则如下：[贴 rules.md 第 1 节]。注意：侧板高度=订单 height_mm，门板宽=width_mm÷door_count，层板宽=width−50mm；背板按薄板单列。输入订单对象列表，输出部件清单（部件名/数量/长×宽/板类型）。附 pytest，以 rules.md 第 5 节样例（1800×550×2200、2门3抽4层）为断言基准。

**验收**：手算 1 单与脚本输出数量级一致（对照 rules.md 第 5 节参考答案，先自己手算再对照）。
**幻觉抽查点**：三种柜体（直型衣柜/悬浮电视柜/书柜）分支是否都实现；书柜无门时门板不输出。

### 3.3 hardware_calc.py

**指令**：
> 写 src/hardware_calc.py：按 [贴 rules.md 第 2 节] 计算每单五金清单。铰链=门扇数×2~3（门高>1m 取 3）；导轨=抽屉数×1 副；拉手=门扇数+抽屉数；螺丝包每柜 1 包；悬浮电视柜加抽屉配件套。输出五金明细 dict（品名/规格/数量）。附 pytest。

**验收**：与 rules.md 第 5 节五金数字一致（铰链 6、导轨 3、拉手 5、螺丝包 1）。
**幻觉抽查点**：门高判断的单位（mm→m 换算别错）。

### 3.4 optimizer.py

**指令**：
> 写 src/optimizer.py：按 [贴 rules.md 第 3 节] 算料。主材（18mm）与背板（9mm 薄板）分开聚合；需求面积=Σ(部件面积×数量)×1.08；张数=ceil(面积÷2.9768㎡)。输入部件清单，输出料单（板种/规格/张数）。附 pytest，断言 rules.md 第 5 节样例：主材 5 张、背板 2 张。

**验收**：与手算一致。
**幻觉抽查点**：ceil 的用法；2.9768 这个数它是否擅自改成 4.93（手册旧笔误，若它见过类似数据可能沿用）。

### 3.5 validator.py（面试爆点模块）

**指令**：
> 写 src/validator.py：按 [贴 rules.md 第 4 节] 校验每个部件长≤2400、宽≤1200；任一违规→整单拦截。reject 记录字段：订单号/客户/柜体类型/违规部件名/方向/实际值/上限/超出量，原因话术按模板。附 pytest，断言 data/orders.xlsx 里的两条埋雷单必被拦截：height_mm=2500 那单卡在侧板长 2500>2400；width_mm=2500 那单卡在门板宽 1250>1200。

**验收**：2 条埋雷订单 100% 被拦截且原因正确（**这是面试演示爆点，不许有任何偏差**）。
**幻觉抽查点**：拦截粒度是"整单"而非单部件；不要把合规单误杀。

### 3.6 report.py

**指令**：
> 写 src/report.py：合规订单输出 output/purchase_list.xlsx（板材料号/规格/张数/五金明细/成本合计），reject 单输出 output/reject_list.xlsx（含原因列）。用 openpyxl，表头加粗、列宽自适应，保证打开排版可读。附最小测试（生成文件存在且可读）。

**验收**：Excel 排版可读；成本合计与手算一致（抽 1 单核对：板材张数×单价 + 五金数量×单价）。
**幻觉抽查点**：openpyxl 样式 API 真实存在；成本公式与 prices.xlsx 单价口径一致（板材按张、五金按个/副/套/包）。

### 3.7 db.py

**指令**：
> 写 src/db.py：采购清单写入 SQLite（bom_items 表：订单号/部件名/尺寸/板材/数量）+ reject_orders 表（订单号/拦截原因）；提供 3 个统计查询函数：本月板材用量 Top5、单均五金成本、拦截订单统计。附 pytest（用 tmp_path 或内存库）。

**验收**：3 条统计 SQL 能跑出数。
**幻觉抽查点**：SQL 日期函数（SQLite 的 strftime 用法）。

### 3.8 main.py

**指令**：
> 写 main.py：CLI 参数 `--input data/orders.xlsx --outdir output/`，按 parser→bom_engine→hardware_calc→validator→optimizer→report→db 串全流程；控制台打印进度与汇总（合规 X 单/拦截 Y 单/总成本 Z 元）。手动 5 单验证端到端。

**验收**：`python main.py --input data/orders.xlsx --outdir output/` 一次跑通。

---

## 4. 会话 9：README

**指令**（手册原文）：
> 请为本项目写 README.md：项目定位（全屋定制拆单自动化的个人演示项目）、业务规则摘要、目录结构、运行方法、工艺拦截演示说明、量化对比结果（手动 X 分钟 vs 脚本 Y 秒，处理 50 单）。要求 HR 和技术面试官都能看懂。

**验收**：量化数字只用你的实测值（先完成 Day 5 量化实测再写）；无虚构数字。
**幻觉抽查点**：运行命令与 main.py 实际参数一致。

---

## 5. 会话 10–12：Day 6 升级包（MySQL + FastAPI）

### 5.1 db.py 改造

**指令**（手册原文）：
> 我的项目 1 里 db.py 目前用 SQLite 存采购清单（见代码，贴上）。请改进：改用 MySQL（SQLAlchemy + pymysql），连接串读环境变量 `DATABASE_URL`，建表 bom_items（订单号/部件名/尺寸/板材/数量）与 reject_orders（订单号/拦截原因）。保持原有统计查询功能（本月板材用量 Top5、单均五金成本、拦截订单统计）不变，语法适配 MySQL。附 pytest 测试（连测试库跑）。

**验收**：跑完 main.py 后 DBeaver 可见 48 条合规入库、2 条埋雷进 reject 表；3 条统计 SQL 出数。
**回退方案**（任务书 Day 6）：MySQL 卡超 2 小时 → 退回 SQLite + FastAPI，数据流叙事不变。

### 5.2 api.py

**指令**（手册原文）：
> 为上面的 MySQL 库写一个 FastAPI 服务 api.py，提供 4 个接口：① GET /orders 订单列表（支持分页）② GET /orders/{order_id}/bom 查单个订单 BOM 明细（含五金与成本合计）③ GET /stats/monthly 月度统计（板材用量 Top5、单均五金成本）④ GET /alerts/rejects 被工艺拦截的订单及原因。每个接口返回 JSON，带异常处理（订单不存在返回 404）。启动后自动生成 /docs 交互文档。附 curl 测试命令。

**验收**：`uvicorn src.api:app --reload` 后 /docs 四接口全调通；height=2500 埋雷单能从 /alerts/rejects 查出原因。
**幻觉抽查点**：SQLAlchemy 2.x 语法（session 用法）；FastAPI 分页参数写法。

### 5.3 API.md

**指令**（手册原文）：
> 根据上面的接口写 API.md：每个接口一段（用途/方法/路径/参数/返回示例），开头加一段架构图（用 ASCII 画：订单Excel → parser → bom_engine → validator → MySQL → FastAPI → 业务方查询），语气面向"想接入这条数据流的同事"。

**验收**：链路完整；每个接口参数/返回示例与实际实现一致。

---

## 6. 🔧 待补区块：Codex 操作细节（你按教程知识库填写，完成后本手册即为成稿）

- [ ] 启动与退出：如何新建会话、恢复上次会话
- [ ] 审批模式：suggest / auto-edit / full-auto 分别何时用（建议：写代码 auto-edit，跑命令逐条确认）
- [ ] 上下文注入：rules.md / orders.xlsx 列结构怎么喂（粘贴 vs 读取本地文件）
- [ ] diff 审查：改动大时看什么（新增文件清单、是否动了无关文件）
- [ ] 验证闭环：如何执行它给的 pytest/运行命令并把报错回贴给它
- [ ] 会话管理：模块间是新会话还是续会话的取舍
- [ ] 常见坑：你实测中发现的 Codex 使用坑（回填到《Codex 落地使用手册》第 5 章）
