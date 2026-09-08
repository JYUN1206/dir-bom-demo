# 交付说明 — 全屋定制拆单自动化

> **个人项目 / 模拟数据**（艾迪尔「AI 数字化应用专员」面试作品）
> 状态：基础版 G1 ✅ / 升级包 G2（SQLite+FastAPI）✅ / 演示资产 G3 🔄（手算耗时改估算口径 ✅、拦截截图 ✅、视频待录）
> 归档日期：2026-09-08

---

## 一、交付物清单

### 1) 可运行代码
| 模块 | 文件 | 职责 |
|---|---|---|
| CLI | `main.py` | 串全流程：parser→bom_engine→hardware_calc→optimizer→validator→report→db |
| 基础版 | `src/parser.py` | 读 Excel + 校验（必填/尺寸>0） |
| 基础版 | `src/bom_engine.py` | 柜体拆解（三种柜型，背板薄板单列） |
| 基础版 | `src/hardware_calc.py` | 五金清单 |
| 基础版 | `src/optimizer.py` | 算料（×1.08，÷2.9768）与成本 |
| 基础版 | `src/validator.py` | 工艺拦截（长>2400/宽>1200 整单拦截） |
| 基础版 | `src/report.py` | 采购清单 + reject 清单 Excel |
| 存储 | `src/db.py` | SQLAlchemy（SQLite 默认 / MySQL 可选）+ 3 统计 |
| 升级包 | `src/api.py` | FastAPI 四接口 + /docs |

### 2) 测试
- `tests/` 9 个测试文件，**49 个 pytest 全部通过**；每模块 ≥3 条用例（验收纪律达标）

### 3) 文档
| 文件 | 用途 |
|---|---|
| `README.md` | HR+技术面试官双读者；运行方法、量化对比、拦截演示 |
| `rules.md` | 业务规则（人工消化版 v1.0） |
| `PRD.md` / `IMPLEMENTATION_PLAN.md` | 需求 / 实施计划 |
| `API.md` | 四接口文档 + ASCII 架构图 |
| `AGENTS.md` | 人机分工约定 |
| `Codex操作手册.md` | agent 协作流程 |
| `DELIVERY.md` | 本文件（交付说明） |

### 4) 数据与配置
- `data/orders.xlsx`（50 单，含 2 埋雷）+ `data/prices.xlsx`
- `scripts/make_sample_data.py`（数据生成器）
- `docker-compose.yml`（可选 MySQL，默认不启用）
- `requirements.txt`、`.gitignore`

### 5) 运行产物（临时，已 git 忽略）
- `output/purchase_list.xlsx`、`output/reject_list.xlsx`、`output/bom.db`

---

## 二、验收结果与关键数字（实测）

### 端到端
| 指标 | 结果 |
|---|---|
| 输入订单 | 50 单 |
| 合规入库 | **48 单** |
| 工艺拦截 | **2 单**（D0001 侧板、D0017 顶板） |
| 板材成本 | 44,790 元 |
| 五金成本 | 7,040 元 |
| **总成本** | **51,830 元** |
| 脚本 50 单耗时 | **≈ 0.09 秒**（5 次均值 86.5–98.8 ms；本机实测） |
| 测试 | **49 passed** |

### 工艺拦截（面试爆点，埋雷 2 条）
```
D0001 客户01：侧板 长2500mm 超机床加工上限 2400mm，整单拦截
D0017 客户17：顶板 长2500mm 超机床加工上限 2400mm，整单拦截
```

### 手算抽核（§5 基准单 1800×550×2200、2门3抽4层）
- 主材 12.21㎡→×1.08→÷2.9768→**5 张**；背板 3.96㎡→**2 张**
- 五金：铰链 6 / 导轨 3副 / 拉手 5 / 螺丝包 1
- 板材 1390 + 五金 216 = **1606 元**（与脚本一致）

---

## 三、业务规则口径（人工消化版关键点）
- 三种柜型：直型衣柜 / 悬浮电视柜 / 书柜；背板 9mm 薄板**单独算料**（竖条拼接，validator 豁免净裁）
- 层板深度缩 50mm（避让，勿与宽度 1~2mm 工艺缝混淆）
- 电视柜抽屉：**外购抽盒口径**——抽面自开料、盒体折"每抽 1 套"五金，不进排样
- 损耗 1.08（锯缝+粗裁余量+缺陷废余料）；标准板 2440×1220 = **2.9768㎡**
- 工艺拦截：任一部件长>2400 或宽>1200 → **整单拦截**；多违规**超长优先**选报一条

---

## 四、升级包说明（无 Docker / 无 MySQL 也可用）
- `src/api.py` 四接口：`GET /orders`(分页) / `GET /orders/{id}/bom` / `GET /stats/monthly` / `GET /alerts/rejects`
- **默认走 SQLite**（`output/bom.db`），无需 Docker/MySQL；设 `DATABASE_URL` 可接 MySQL
- 已本地实测：`/docs` 200、四接口正常、404 正确、埋雷可从 `/alerts/rejects` 查出
- 本环境 Docker Desktop 为 paused 状态，未启用 MySQL（走手册 5.1 回退：SQLite+FastAPI）

---

## 五、遗留事项（G3 演示资产，待人工）
- [x] ~~手算 5 单耗时实测~~ → **用户决策（2026-09-08）：演示项目采用估算口径**。README 保留「约 40 分钟」并明确标注「估算、非实测」；`手算实测工作表.md` 转为面试前自练材料（可选，不算交付项）
- [ ] 3-5 分钟演示视频（唯一待办，需人工录制，脚本见 `G3_CHECKLIST.md` 第二节）
- [x] **2 条工艺拦截截图**：`screenshots/reject_terminal.png`（端到端运行）+ `reject_excel.png`（拦截明细），由 `scripts/make_screenshots.py` 从真实运行输出渲染，可随时重跑再生成；面试前可选 Cmd+Shift+4 重截原生屏摄
- [ ] （可选）埋雷 2"宽超 1200mm"单独演示，若面试需覆盖两个维度

---

## 六、Git 状态
- 本地 `main` 分支，5 个提交（chore 文档 / feat(bom) 基础版 / feat(api) 升级包 / docs 交付说明 / docs G3 演示资产），工作区干净
- `.gitignore`：忽略 `.venv/`、`output/`、`__pycache__/`、`.pytest_cache/`、`.DS_Store`
- **已推送远程**：https://github.com/JYUN1206/dir-bom-demo （public，任务书 Day 3 指定仓库名；本机直连 GitHub 超时，经系统代理 127.0.0.1:7897 推送成功）
