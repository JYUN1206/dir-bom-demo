# 全屋定制拆单自动化（订单 Excel → 自动拆 BOM → 算料 → 五金 → 工艺拦截 → 入库）

> **个人项目 / 模拟数据** —— 演示"业务规则人工设计 + AI 写代码 + 人工验收"的岗位工作方式。
> 拆单规则为人工设计的**简化模型**，真实拆单规则以贵司工艺为准。

## 这是什么

一套把「全屋定制柜体订单」自动拆成「采购清单」的脚本：输入一张订单 Excel，程序按人工定下的拆单规则，把每个柜体拆成部件、算出板材用量与五金清单、合并成本、并拦截超出机床加工上限的订单，最终输出采购清单 Excel 与拦截清单，同时入库 SQLite 可供统计查询。

一句话：**把拆单员几十分钟的手工拆单，压缩到约 0.1 秒跑完，且规则可解释、可拦截、可追溯。**

## 业务规则摘要（人工设计的简化模型）

- **拆解**：把每柜拆成顶板/底板/左右侧板/层板/门板(或抽屉面板)/背板；层板深度缩 50mm 避让；背板按 9mm 薄板单独算料（竖条拼接，不参与单块净裁）。
- **五金**：铰链=门扇数×(门高>1m 取3，否则2)；导轨=抽屉数×1副；拉手=门扇+抽屉；每柜 1 包螺丝包；悬浮电视柜另配抽屉配件套（外购抽盒口径）。
- **算料**：需求面积 = Σ(部件面积) × 1.08 损耗；标准板 2440×1220 = 2.9768㎡，张数向上取整拍整；主材与背板分开算。
- **成本**：板材按张、五金按个/副/套/包，各乘单价汇总（单价来自 `prices.xlsx`）。
- **工艺拦截**：任一部件的长 >2400mm 或宽 >1200mm → **整单拦截**（背板豁免）；同一订单多违规时超长优先。

## 量化对比

| 项目 | 耗时 | 来源 |
|---|---|---|
| 人工拆单（手算 5 单） | **约 40 分钟（估算）** | ⚠️ 估算值，**面试前请实测替换** |
| 脚本拆单（50 单，本机实测） | **≈ 0.09 秒** | 实测（`run()` 5 次均值 86.5–98.8 ms） |

> ⚠️ **真实口径**：脚本耗时 0.09 秒为**本机实测**；人工手算 40 分钟为**估算区间，非实测**。提交/面试前请按 `Codex操作手册.md` 会话 9 实测 5 单并替换下方 `手算 5 单 =`，且手工改掉表格里的估算值。

## 运行方法

```bash
# 1. 环境
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
# 2. (可选) 重新生成模拟数据(默认已带 data/orders.xlsx, prices.xlsx)
.venv/bin/python scripts/make_sample_data.py
# 3. 端到端跑 50 单
.venv/bin/python main.py --input data/orders.xlsx --outdir output/ --db output/bom.db
# 4. 跑全部测试
.venv/bin/python -m pytest tests/ -q
```

一次运行会产出：
- `output/purchase_list.xlsx` —— 板材 / 五金 / 汇总 三页，含成本合计
- `output/reject_list.xlsx` —— 被拦截订单及原因
- `output/bom.db` —— SQLite 库（`bom_items`+`hardware_items`+`reject_orders`），供统计查询

## 工艺拦截演示（面试爆点）

模拟 50 单中刻意埋 2 条工艺违规订单，用于演示拦截能力：

| 订单 | 埋雷 | 拦截结果 |
|---|---|---|
| D0001 | 柜高 2500mm | 侧板 长2500mm 超 2400mm → **整单拦截** |
| D0017 | 柜宽 2500mm、2 门 | 顶板 长2500mm 超 2400mm → **整单拦截** |

被拦截的订单不进采购与入库，原因话术形如：
`D0001 客户01：侧板 长2500mm 超机床加工上限 2400mm，整单拦截`

> 说明：两雷在"超长优先"口径下均报超长；如要单独演示"宽超 1200mm"，可调整埋雷柜型。

## 升级包：FastAPI 查询服务（默认 SQLite，含可选 MySQL）

基础版之外，另有一层 FastAPI 查询服务（`src/api.py`），把「订单 Excel → 拆 BOM → 拦截 → 入库」的数据流开放成 4 个 JSON 接口，供下游（采购/生产/报工）查询：

- `GET /orders` —— 订单列表（分页）
- `GET /orders/{order_id}/bom` —— 单订单 BOM 明细（含五金与成本）
- `GET /stats/monthly` —— 本月板材 Top5、单均五金成本
- `GET /alerts/rejects` —— 被工艺拦截订单及原因（埋雷单由此查出）

```bash
# 1) 先跑一遍, 把 48 合规 + 2 拦截写入 SQLite
.venv/bin/python main.py --input data/orders.xlsx --outdir output/
# 2) 启动服务(默认读 SQLite, 无需 MySQL)
.venv/bin/uvicorn src.api:app --reload   # /docs 可交互调试
```

数据源默认 SQLite（`output/bom.db`）；如需 MySQL 可设环境变量 `DATABASE_URL`（自带 `docker-compose.yml`，可选）。接口细节见 `API.md`。

## 目录结构

```
项目1-全屋定制拆BOM脚本/
├── main.py                # CLI 入口(串全流程)
├── src/
│   ├── parser.py          # 读 Excel + 校验
│   ├── bom_engine.py      # 柜体拆解
│   ├── hardware_calc.py   # 五金清单
│   ├── optimizer.py       # 算料/成本
│   ├── validator.py       # 工艺拦截
│   ├── report.py          # 采购 + reject Excel
│   └── db.py              # SQLite 入库 + 统计
├── tests/                 # pytest(39 条, 每模块≥3)
├── data/                  # orders.xlsx / prices.xlsx(模拟)
├── scripts/               # make_sample_data.py(造数据)
├── output/                # 报表与库(运行产物, git 忽略)
├── rules.md / PRD.md / IMPLEMENTATION_PLAN.md   # 规则与计划
└── Codex操作手册.md        # AI agent 协作流程
```

## 模块流水线

```
data/orders.xlsx
  └→ parser → bom_engine → hardware_calc
                          └→ optimizer → validator → report → output/*.xlsx
                                                     └→ db(SQLite) → 统计查询
```

## 本项目的定位（面向 HR / 面试官）

这不是工厂级拆单软件，而是**方法论的演示**：人工把业务规则设计清楚 → AI 据此逐模块写代码并带测试 → 人工手算核对、实测对比、验收放行。核心价值在于"业务规则如何转成可靠系统、并在工艺边界上正确拦截"，适合展现拆单/数据结构化/流程自动化的能力。面试口径：规则为简化模型，真实拆单以贵司工艺为准。

---
*运行命令与 `main.py` 实际参数一致(`--input` / `--outdir` / `--db` / `--prices`)。量化数字只用实测值。*
