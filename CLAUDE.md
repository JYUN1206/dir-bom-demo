# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目定位

全屋定制订单自动拆 BOM 的个人演示项目（Python 实现），分两个阶段：

1. **基础版（3 天）**：订单 Excel → 拆 BOM → 算料（含损耗）→ 五金清单 → 工艺拦截 → SQLite 入库 + 采购清单 Excel
2. **升级包（1 天，强烈建议做）**：SQLite → MySQL（SQLAlchemy + pymysql），新增 FastAPI 查询服务。目的：JD 职责 3 收尾句要求"对接酷家乐/三维家、ERP、MES 生产系统，实现数据一键流转"，技能标签含 MySQL——基础版只到 SQLite + Excel，缺"系统对接"实证。升级包把数据流补完整：`订单 Excel → BOM 计算 → MySQL 入库 → API 查询`。真实对接酷家乐需企业认证做不了，此模拟链路是家里可演示的版本。

这是艾迪尔「AI 数字化应用专员」面试的核心作品，演示"业务规则人工设计 + AI 写代码 + 人工验收调试"的岗位工作方式。

## 关键纪律

1. **分工标注**：手册中标 🤖 的步骤交给 agent 执行，标 ✅ 的由人工完成/确认。业务规则必须由人工先写清（rules.md），不让 AI 猜业务。
2. **小步验收**：一次只开发一个模块，验收通过后再进行下一个；每个模块必须附 pytest 测试。
3. **红线**：
   - 量化数字只用实测值（手动耗时 vs 脚本耗时），不外推编造。**已记录例外（2026-09-08 用户决策）**：人工手算基线采用估算口径（README 已标注「估算、非实测」），脚本侧数字仍全部实测；后续 agent 不得把 README 估算值改回「实测」或反向覆盖标注
   - 项目标注「个人项目 / 模拟数据」
   - 面试话术明确"业务规则是简化模型，真实拆单规则以贵司工艺为准"
4. **埋雷演示**：模拟数据必须埋 2 条工艺违规订单——一条 `height_mm=2500`（侧板超 2400 上限）、一条 `width_mm=2500`（顶板长 2500 超上限；超长优先口径下报超长，门板宽 1250 超宽被屏蔽）。validator 能拦截并给出原因是面试演示爆点；升级包验收时这 2 条雷也要进 reject 表并能通过 API 查出。

## 业务规则摘要（详见 rules.md）

**柜体拆解**（直型衣柜示例）：
- 顶板/底板：宽 × 深，各 1 块；左右侧板：深 × 高，各 1 块
- 背板：宽 × 高，1 块（薄板）；层板：(宽−50mm) × 深，n 块
- 门板：(宽 ÷ 门扇数) × 高，均分

**五金**：铰链 = 门扇数 × 2~3（门高 >1m 取 3）；导轨 = 抽屉数 × 1 副；拉手 = 门扇数 + 抽屉数；每柜 1 包螺丝/连接件。

**算料**：板材面积 = Σ(部件面积) × 1.08 损耗；张数 = ceil(面积 ÷ 2.9768㎡)（2440×1220mm 单张，以 rules.md 为准）。

**工艺拦截**：单部件长 ≤2400mm、宽 ≤1200mm，超出 → 整单拦截进 reject 清单并注明原因。

## 基础版模块开发顺序与验收标准

| 顺序 | 模块 | 职责 | 验收 |
|---|---|---|---|
| 1 | src/parser.py | 读 Excel + 校验必填字段/数值（尺寸>0） | 50 行全解析，空值/负数报错 |
| 2 | src/bom_engine.py | 柜体拆解算法 | 手算 1 单（如 1800×550×2200、2门3抽4层）核对一致 |
| 3 | src/hardware_calc.py | 五金清单计算 | 与五金规则一致 |
| 4 | src/optimizer.py | 算料（含 1.08 损耗、ceil 张数） | 与手算一致 |
| 5 | src/validator.py | 工艺冲突校验拦截 | 2 条埋雷订单被拦截且原因正确 |
| 6 | src/report.py | 输出采购清单 Excel + reject 清单 | 排版可读，成本合计与手算一致 |
| 7 | src/db.py | SQLite 入库 + 统计查询 | 板材 Top5 / 单均五金成本 / 拦截统计 3 条 SQL 跑通 |
| 8 | main.py | CLI 串接全流程 | 端到端运行成功 |

## 升级包：MySQL + FastAPI 数据流（1 天）

> **实际执行口径**：按手册 5.1 回退方案，db.py 默认 SQLite、设 `DATABASE_URL` 可切 MySQL；docker-compose.yml 为可选环境。以下步骤保留为 MySQL 可选路径的说明。

### 步骤与验收

| 步骤 | 内容 | 验收 |
|---|---|---|
| 1. MySQL 环境 | Docker Desktop + docker-compose.yml 起 MySQL 8.0（库 bom_db），DBeaver 连通 | `docker compose up -d` 后 DBeaver 能连 |
| 2. 改造 db.py | SQLite → MySQL（SQLAlchemy + pymysql），连接串读环境变量 `DATABASE_URL`；建表 bom_items（订单号/部件名/尺寸/板材/数量）与 reject_orders（订单号/拦截原因）；统计查询功能不变、语法适配 MySQL；附 pytest（连测试库跑） | 跑完 main.py 后 DBeaver 可见 48 条合规入库、2 条埋雷进 reject 表；3 条统计 SQL 出数 |
| 3. FastAPI 服务 | 新增 api.py，4 个接口：① GET /orders（分页）② GET /orders/{order_id}/bom（BOM 明细含五金与成本合计）③ GET /stats/monthly（板材 Top5、单均五金成本）④ GET /alerts/rejects（被拦截订单及原因）；JSON 返回、404 异常处理、自动 /docs | `uvicorn api:app --reload` 后 /docs 里 4 接口全调通；height=2500 埋雷订单能从 /alerts/rejects 查出拦截原因 |
| 4. 写 API.md | 每接口一段（用途/方法/路径/参数/返回示例）+ 开头 ASCII 架构图（订单Excel → parser → bom_engine → validator → MySQL → FastAPI → 业务方查询），语气面向"想接入数据流的同事" | 接口文档完整可读 |

### 升级包产出物（本目录内新增）

```
├── src/api.py          # FastAPI 查询服务（新增）
├── docker-compose.yml  # 一键起 MySQL（新增）
├── API.md              # 接口文档（新增）
└── src/db.py           # 改造：SQLite → MySQL
```

注：GitHub 发布到 `idir-ai-toolkit` 时，本目录整体对应 `scripts/bom-splitter/`。

## 产出物（基础版）

```
项目1-全屋定制拆BOM脚本/
├── README.md          # 业务背景、规则、运行方法、量化对比（人工 X 分钟 vs 脚本 Y 秒，50 单）
├── data/              # orders.xlsx（50 行模拟订单，含 2 条埋雷）、prices.xlsx
├── rules.md           # 拆单业务规则（人工编写）
├── src/               # parser / bom_engine / hardware_calc / optimizer / validator / report / db / api
├── output/            # 采购清单、reject 清单、统计报表
├── main.py            # CLI 入口
├── docker-compose.yml # MySQL 环境
└── API.md             # 接口文档
```

## 常用命令

```bash
# 环境准备
pip install -r requirements.txt

# 基础版运行与测试
python main.py --input data/orders.xlsx --outdir output/
pytest
pytest tests/test_parser.py                # 单个模块测试

# 升级包：MySQL 与 API
docker compose up -d                       # 起 MySQL 8.0（root 密码 bom123456，库 bom_db，端口 3306）
export DATABASE_URL='mysql+pymysql://root:bom123456@localhost:3306/bom_db'
python main.py --input data/orders.xlsx    # 入库 MySQL
uvicorn src.api:app --reload               # 起 FastAPI，浏览器开 http://127.0.0.1:8000/docs
```

## 模拟数据规格

orders.xlsx 列：order_id, customer, cabinet_type（直型衣柜/悬浮电视柜/书柜）, width_mm/depth_mm/height_mm, board_material（颗粒板18mm/多层板18mm）, door_count, drawer_count, shelf_count, hinge_spec。共 50 行。

## 当前状态（2026-09-08）

基础版 + 升级包 + 演示资产全部完成并推送远程（https://github.com/JYUN1206/dir-bom-demo）。原「待完成步骤」6 项已全部处置，详见 `DELIVERY.md`（含两项用户决策：手算基线改估算口径、演示视频暂缓）。

## 面试呈现话术

- 基础版："我用 Codex/Claude Code 复刻了贵司职责 3 的场景：这是 50 单模拟订单，脚本自动拆 BOM、算料含损耗、五金清单和成本，还内置了工艺校验——这两单因为超机床加工上限被自动拦截了。"
- 升级包："职责 3 说要对接酷家乐、ERP、MES 实现数据一键流转。真实对接需要贵司的企业账号和系统权限，我在家里先用同构链路跑通了：订单数据进来 → 自动拆 BOM → 工艺校验 → 入 MySQL 库 → FastAPI 接口供下游查询。入职后把输入源换成酷家乐导出、把库换成贵司 ERP，这条链路直接就能用——接口文档我都写好了。"（加分动作：现场打开 /docs 调一个接口）
