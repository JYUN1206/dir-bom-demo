"""FastAPI 查询服务(升级包 Day 6)。数据源默认读 DATABASE_URL, 缺省回退 SQLite。

个人项目 / 模拟数据 —— 简化业务模型，真实拆单规则以贵司工艺为准。
启动:
  1. (推荐)先跑 main.py 把 48 合规 + 2 拦截写入 DATABASE_URL 指向的库
  2. uvicorn src.api:app --reload   (默认回退 output/bom.db 的 SQLite)
  3. 浏览器打开 http://127.0.0.1:8000/docs
"""
from __future__ import annotations

import os

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse
from sqlalchemy.exc import OperationalError

from src.db import (
  connect,
  avg_hardware_cost,
  get_all_order_ids,
  get_order_bom,
  get_orders_page,
  get_rejects,
  init_db,
  monthly_board_top5,
)

app = FastAPI(
  title='全屋定制拆单 BOM 查询服务',
  description='订单 BOM 明细 / 月度统计 / 工艺拦截告警查询（个人项目/模拟数据）。',
  version='1.0.0',
)


def get_engine():
  path = os.environ.get('BOM_DB_PATH', 'output/bom.db')
  return connect(path)


def _ensure_db():
  engine = get_engine()
  try:
    with engine.connect() as conn:
      conn.exec_driver_sql('SELECT 1')
  except OperationalError:
    raise HTTPException(status_code=503,
                        detail='数据库暂不可用，请先运行 main.py 生成本地 SQLite(output/bom.db) 或配置 DATABASE_URL')


@app.get('/health')
def health():
  return {'status': 'ok'}


@app.get('/orders')
def list_orders(
  page: int = Query(1, ge=1, description='页码, 从 1 开始'),
  page_size: int = Query(20, ge=1, le=100, description='每页条数'),
):
  """① GET /orders:订单列表(分页)。"""
  _ensure_db()
  rows = get_orders_page(get_engine(), page=page, page_size=page_size)
  ids = get_all_order_ids(get_engine())
  total = len(ids)
  return {
    'page': page,
    'page_size': page_size,
    'total': total,
    'items': rows,
  }


@app.get('/orders/{order_id}/bom')
def order_bom(order_id: str):
  """② GET /orders/{order_id}/bom:单订单 BOM 明细(含五金)。"""
  engine = get_engine()
  ids = get_all_order_ids(engine)
  if order_id not in ids:
    raise HTTPException(status_code=404, detail=f'订单 {order_id} 不存在')
  bom = get_order_bom(engine, order_id)
  hw_cost = round(sum(h['cost'] for h in bom['hardware']), 2)
  bom['hardware_cost'] = hw_cost
  return {'order_id': order_id, **bom}


@app.get('/stats/monthly')
def stats_monthly():
  """③ GET /stats/monthly:本月板材用量 Top5 + 单均五金成本。"""
  _ensure_db()
  engine = get_engine()
  return {
    'board_top5': monthly_board_top5(engine),
    'avg_hardware_cost': avg_hardware_cost(engine),
  }


@app.get('/alerts/rejects')
def alerts_rejects():
  """④ GET /alerts/rejects:被工艺拦截的订单及原因。"""
  _ensure_db()
  return {'rejects': get_rejects(get_engine())}


@app.get('/favicon.ico', include_in_schema=False)
def _favicon():
  return JSONResponse(status_code=204, content=None)
