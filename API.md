# 拆单 BOM 查询服务 — API 说明

> 个人项目 / 模拟数据。面向想接入这条数据流的下游同事：看完本文即可把 BOM 明细、月度统计、工艺拦截告警接进你们的系统。

## 架构图

```
┌──────────────┐    ┌──────────┐    ┌────────────┐    ┌───────────┐
│ 订单 Excel    │ →  │ parser   │ →  │ bom_engine │ →  │ validator │
│ orders.xlsx  │    │(读+校验) │    │(拆部件)     │    │(工艺拦截)  │
└──────────────┘    └──────────┘    └────────────┘    └─────┬─────┘
                                                            │ 合规单
                                              ┌─────────────▼─────────────┐
                                              │  MySQL / SQLite           │
                                                                                            │  bom_items  reject_orders │
                                              └─────────────┬─────────────┘
                                                            │ 查询
                                              ┌─────────────▼─────────────┐
                                              │   FastAPI  (本服务)        │
                                              │   /orders  /bom  /stats    │
                                              │   /alerts/rejects /docs    │
                                              └─────────────┬─────────────┘
                                                            │ JSON
                                              ┌─────────────▼─────────────┐
                                              │   业务方(生产/采购/报工)    │
                                              └───────────────────────────┘
```

链路说明：订单 Excel 经 parser 校验 → bom_engine 拆成部件 → validator 工艺拦截 → 合规单写库；本 FastAPI 服务对外提供查询。被拦截订单只进 `reject_orders`，通过 `/alerts/rejects` 暴露。

## 快速开始(默认无需 Docker/MySQL)

```bash
# 1) 端到端跑一遍, 把 48 合规 + 2 拦截写入 SQLite(output/bom.db)
.venv/bin/python main.py --input data/orders.xlsx --outdir output/

# 2) 启动服务(默认读 output/bom.db, 不依赖 Docker/MySQL)
.venv/bin/uvicorn src.api:app --reload
# 浏览器打开 http://127.0.0.1:8000/docs 即可交互调试
```

数据源优先级：环境变量 `DATABASE_URL`（如接 MySQL 时设 `mysql+pymysql://root:bom123456@localhost:3306/bom_db`）> `BOM_DB_PATH`（默认 `output/bom.db` 的 SQLite）。**默认走 SQLite，无需 MySQL；** 需要 MySQL 时才设 `DATABASE_URL` 并按 `docker-compose.yml` 自备 MySQL 实例。

---

## 接口一览

| 方法 | 路径 | 用途 |
|---|---|---|
| GET | `/orders` | 订单列表（分页） |
| GET | `/orders/{order_id}/bom` | 单订单 BOM 明细（含五金与成本） |
| GET | `/stats/monthly` | 月度统计（板材 Top5、单均五金成本） |
| GET | `/alerts/rejects` | 被工艺拦截订单及原因 |

所有接口返回 `application/json`；资源不存在返回 `404`。

---

### ① GET /orders —— 订单列表（分页）

**用途**：分页拉取已合规处理完成的订单清单，适合采购/生产侧先看有哪些订单。

**参数**

| 名 | 类型 | 必填 | 默认 | 说明 |
|---|---|---|---|---|
| `page` | int | 否 | 1 | 页码，从 1 开始 |
| `page_size` | int | 否 | 20 | 每页条数，1–100 |

**返回示例**

```json
{
  "page": 1,
  "page_size": 2,
  "total": 48,
  "items": [
    { "order_id": "D0002", "part_count": 5, "area_m2": 6.225 },
    { "order_id": "D0003", "part_count": 6, "area_m2": 19.25 }
  ]
}
```

`part_count`=该单部件数，`area_m2`=该单板材面积合计（㎡）。

---

### ② GET /orders/{order_id}/bom —— 单订单 BOM 明细

**用途**：查某订单拆解出的部件清单与五金明细及五金成本合计。

**参数**

| 名 | 类型 | 说明 |
|---|---|---|
| `order_id` | path string | 订单号，如 `D0002` |

**返回示例**

```json
{
  "order_id": "D0002",
  "parts": [
    { "part_name": "顶板", "length_mm": 2000, "width_mm": 550,
      "board_type": "主材18mm", "board_material": "颗粒板18mm", "quantity": 1 },
    { "part_name": "背板", "length_mm": 2200, "width_mm": 2000,
      "board_type": "背板9mm", "board_material": "背板9mm", "quantity": 1 }
  ],
  "hardware": [
    { "item_name": "铰链", "quantity": 6, "unit": "个", "unit_price": 8.5, "cost": 51.0 }
  ],
  "hardware_cost": 216.0
}
```

`hardware_cost` = 该单五金成本合计；拦截单（无 BOM）返回 `404`。

---

### ③ GET /stats/monthly —— 月度统计

**用途**：给采购本科提供本月板材用量榜单与单均五金成本。

**返回示例**

```json
{
  "board_top5": [
    { "material": "多层板18mm", "area_m2": 156.2329, "parts": 199 },
    { "material": "颗粒板18mm", "area_m2": 154.2669, "parts": 217 },
    { "material": "背板9mm", "area_m2": 119.128, "parts": 48 }
  ],
  "avg_hardware_cost": 146.67
}
```

`board_top5` 按板材料号汇总面积降序 Top5；`avg_hardware_cost` = 五金成本合计 ÷ 有五金订单数。

---

### ④ GET /alerts/rejects —— 工艺拦截告警

**用途**：暴露被工艺校验整单拦截的订单及原因，供复核/打回班组处理。

**返回示例**

```json
{
  "rejects": [
    {
      "order_id": "D0001",
      "customer": "客户01",
      "cabinet_type": "直型衣柜",
      "part_name": "侧板",
      "direction": "长",
      "value_mm": 2500,
      "limit_mm": 2400,
      "reason": "D0001 客户01：侧板 长2500mm 超机床加工上限 2400mm，整单拦截"
    }
  ]
}
```

---

## 前置条件与口径

- 数据先由 `main.py` 跑一遍写入（否则各接口返回 `503`，提示先入库）。
- 被拦截订单只进 `reject_orders`，`/orders` 不含拦截单，拦截单 BOM 接口返回 `404`。
- 全部为【个人项目 / 模拟数据】，统计基于人工设计的简化规则（主材项目面积为部件长×宽×数量）。
