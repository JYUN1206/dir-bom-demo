# 实施计划 — 全屋定制拆 BOM（issue 拆分版）

> 依据：PRD.md + CLAUDE.md 模块顺序 + 7 天冲刺排期（Day 3-6 为本项目窗口）
> 拆分原则：**垂直切片**——每个 issue 独立可开发、可测试、可验收，做完一个勾一个
> 分工标注：🤖 = agent 执行，✅ = 人工完成/确认
> 状态标记：⬜ 未开始 / 🔄 进行中 / ✅ 完成

## Issue 0：前置阻塞项（不完成不许开编码）⬜

| 任务 | 分工 | 验收 |
|---|---|---|
| rules.md 人工消化：逐条回答 §6 的 7 个问题，用自己的话改写 | ✅ | 脱稿讲出每条规则"为什么"（Day 3 验收线） |
| 造 orders.xlsx 50 行（含 2 埋雷：height=2500 / width=2500）+ prices.xlsx | ✅/🤖 | 埋雷字段核对无误；50 行覆盖 3 种柜型、2 种板材 |
| 建 GitHub 仓库 `dir-bom-demo`；酷家乐画 1 柜截图 | ✅ | 仓库可访问，截图留档 |

## Issue 1：parser（Day 4 上午）⬜

- 🤖 `src/parser.py` + `tests/test_parser.py`
- 垂直切片：读 orders.xlsx → 返回 Order 对象列表
- 验收：50 行全解析；缺列/空值/负尺寸抛 ValueError 且报错信息含订单号
- pytest ≥3：正常解析 / 空值报错 / 负数报错

## Issue 2：bom_engine（Day 4）⬜

- 🤖 `src/bom_engine.py` + `tests/test_bom_engine.py`
- 切片：1 单 → 部件清单（名称/长/宽/数量/板材/薄厚）
- 验收：**手算基准单逐件核对**（1800×550×2200，2门3抽4层 → 顶/底/侧×2/层×4/门×2/背，面积合计 12.21 + 3.96㎡）
- pytest ≥3：衣柜基准 / 电视柜抽屉面板 / 书柜无门默认

## Issue 3：hardware_calc（Day 4）⬜

- 🤖 `src/hardware_calc.py` + `tests/test_hardware_calc.py`
- 验收：基准单 → 铰链 6、导轨 3 副、拉手 5、螺丝包 1；电视柜含抽屉配件套
- pytest ≥3：门高>1m 取 3 铰链 / 门高≤1m 取 2 / 电视柜抽屉套

## Issue 4：optimizer（Day 5）⬜

- 🤖 `src/optimizer.py` + `tests/test_optimizer.py`
- 切片：部件清单 → 板材张数（主材/背板分开）+ 成本
- 验收：基准单主材 5 张、背板 2 张（13.19㎡ / 4.28㎡，÷2.9768 ceil）
- pytest ≥3：损耗计算 / ceil 边界 / 主背板分离

## Issue 5：validator（Day 5，演示爆点）⬜

- 🤖 `src/validator.py` + `tests/test_validator.py`
- 验收：2 条埋雷被拦截，原因话术 = `{order_id} {customer}：{部件名} {方向}{实际值}mm 超机床加工上限 {上限}mm，整单拦截`
- pytest ≥3：height=2500 拦侧板 / width=2500 拦门板 / 正常单放行
- **留档**：终端输出截图（面试用）

## Issue 6：report（Day 5）⬜

- 🤖 `src/report.py`：采购清单 Excel + reject 清单 Excel 到 output/
- 验收：排版可读；成本合计与手算一致
- pytest ≥3：文件生成 / 合计正确 / reject 清单含 2 条

## Issue 7：db + main 端到端（Day 5）⬜

- 🤖 `src/db.py`（SQLite 版）+ `main.py` CLI
- 验收：`python main.py --input data/orders.xlsx --outdir output/` 50 单一次跑通；3 条统计 SQL（板材 Top5 / 单均五金成本 / 拦截统计）出数
- **留档**：量化实测——✅手算 5 单记耗时 vs 🤖脚本 50 单记耗时，写入 README

## Issue 8：README + 演示视频（Day 5 晚）⬜

- 🤖 README.md（HR + 技术面试官双读者）｜✅录 3-5 分钟演示视频
- 验收：含量化对比、运行方法、埋雷演示说明；标注「个人项目/模拟数据」

## Issue 9：升级包 A — MySQL（Day 6）⬜

- 🤖 docker-compose.yml（MySQL 8.0，bom_db）+ db.py 改造（`DATABASE_URL` 环境变量，pymysql 方言）
- 验收：DBeaver 连通；跑完 main.py 后 48 条入 bom_items、2 条入 reject_orders；3 条统计 SQL 适配 MySQL 出数
- 熔断：卡超 2 小时 → 退 SQLite + FastAPI

## Issue 10：升级包 B — FastAPI + API.md（Day 6）⬜

- 🤖 `src/api.py` 四接口 + `API.md`（含 ASCII 架构图：订单Excel → parser → bom_engine → validator → MySQL → FastAPI → 业务方）
- 验收：`uvicorn src.api:app --reload` 后 /docs 四接口全调通；height=2500 埋雷能从 /alerts/rejects 查出原因；404 正常
- **留档**：2 分钟 API 演示视频 / 截图

## 依赖关系

```
Issue 0（人工规则+数据）
  └─→ 1 parser → 2 bom_engine → 3 hardware_calc
              ↓（2 可与 3 并行）
        4 optimizer → 5 validator → 6 report → 7 db+main
                                              ↓
                                    8 README/视频
                                    9 MySQL（依赖 7）
                                    10 FastAPI（依赖 9）
```

## 全局纪律（每个 issue 完成时自检）

- [ ] pytest 全绿且 ≥3 条
- [ ] 量化数字实测，不编造
- [ ] 产出标注「个人项目/模拟数据」
- [ ] 小步验收后才开下一个 issue
- [ ] 截图/日志留档
