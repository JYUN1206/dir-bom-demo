"""数据持久化(save via SQLAlchemy 2.x):SQLite 或 MySQL 均可。

个人项目 / 模拟数据 —— 简化业务模型，真实拆单规则以贵司工艺为准。
后端选择(优先级):
  1. 显式传入的 ConnectionString(测试用);
  2. 环境变量 DATABASE_URL(如 mysql+pymysql://root:pwd@host:3306/bom_db);
  3. 回退本地 SQLite(--db 指向路径或 :memory:),保证无 MySQL 也能跑通"SQLite+FastAPI"。
表:bom_items / hardware_items / reject_orders。统计查询适配 SQLite(strftime) 与
MySQL(DATE_FORMAT) 两种方言。
"""
from __future__ import annotations

import os

from sqlalchemy import (
  Column,
  Float,
  Integer,
  MetaData,
  String,
  Table,
  create_engine,
  text,
)
from sqlalchemy.pool import StaticPool

metadata = MetaData()

bom_items = Table(
  'bom_items', metadata,
  Column('id', Integer, primary_key=True, autoincrement=True),
  Column('order_id', String(50), nullable=False),
  Column('part_name', String(50), nullable=False),
  Column('length_mm', Integer, nullable=False),
  Column('width_mm', Integer, nullable=False),
  Column('board_type', String(50), nullable=False),
  Column('board_material', String(50), nullable=False),
  Column('quantity', Integer, nullable=False),
  Column('created_at', String(30), nullable=False),
)

hardware_items = Table(
  'hardware_items', metadata,
  Column('id', Integer, primary_key=True, autoincrement=True),
  Column('order_id', String(50), nullable=False),
  Column('item_name', String(50), nullable=False),
  Column('quantity', Integer, nullable=False),
  Column('unit', String(10), nullable=False),
  Column('unit_price', Float, nullable=False),
  Column('cost', Float, nullable=False),
  Column('created_at', String(30), nullable=False),
)

reject_orders = Table(
  'reject_orders', metadata,
  Column('id', Integer, primary_key=True, autoincrement=True),
  Column('order_id', String(50), nullable=False),
  Column('customer', String(50), nullable=False),
  Column('cabinet_type', String(50), nullable=False),
  Column('part_name', String(50), nullable=False),
  Column('direction', String(10), nullable=False),
  Column('value_mm', Integer, nullable=False),
  Column('limit_mm', Integer, nullable=False),
  Column('reason', String(255), nullable=False),
  Column('created_at', String(30), nullable=False),
)


def database_url(path=None, override=None):
  """解析连接串:override > DATABASE_URL 环境变量 > 本地 SQLite。"""
  if override:
    return override
  env = os.environ.get('DATABASE_URL')
  if env:
    return env
  return f'sqlite:///{path if path else ":memory:"}'


def connect(path=None, override=None):
  """创建 engine(路径用于 SQLite 回退, override 强制连接串)。

  内存 SQLite 用 StaticPool, 保证所有连接共享同一实例(测试/FastAPI 单库)。
  """
  url = database_url(path, override)
  if url == 'sqlite:///:memory:':
    return create_engine(url, future=True, poolclass=StaticPool,
                         connect_args={'check_same_thread': False})
  return create_engine(url, future=True)


def init_db(engine):
  metadata.create_all(engine)


def _insert(engine, table, rows):
  if not rows:
    return
  with engine.begin() as conn:
    conn.execute(table.insert(), rows)


def insert_bom_items(engine, order, parts):
  _insert(engine, bom_items, [
    {
      'order_id': order.order_id, 'part_name': part.name,
      'length_mm': part.length_mm, 'width_mm': part.width_mm,
      'board_type': part.board_type,
      'board_material': order.board_material if part.board_type == '主材18mm' else '背板9mm',
      'quantity': part.count, 'created_at': _now(),
    }
    for part in parts
  ])


def insert_hardware(engine, order, items, prices):
  _insert(engine, hardware_items, [
    {
      'order_id': order.order_id, 'item_name': item.name,
      'quantity': item.quantity, 'unit': item.unit,
      'unit_price': prices[item.name]['price'],
      'cost': round(item.quantity * prices[item.name]['price'], 2),
      'created_at': _now(),
    }
    for item in items
  ])


def insert_reject(engine, reject):
  _insert(engine, reject_orders, [{
    'order_id': reject.order_id, 'customer': reject.customer,
    'cabinet_type': reject.cabinet_type, 'part_name': reject.part_name,
    'direction': reject.direction, 'value_mm': reject.value_mm,
    'limit_mm': reject.limit_mm, 'reason': reject.reason, 'created_at': _now(),
  }])


def save_all(engine, results, rejects, prices):
  """批量入库:合规单写 bom_items+hardware_items, 拦截单写 reject_orders。"""
  for result in results:
    insert_bom_items(engine, result.order, result.parts)
    insert_hardware(engine, result.order, result.hardware, prices)
  for reject in rejects:
    insert_reject(engine, reject)


def _now():
  from datetime import datetime
  return datetime.now().strftime('%Y-%m-%d %H:%M:%S')


def _rows(rows):
  # Row 用 _mapping; RowMapping 直接用(兼容两种调用方式)
  return [dict(r._mapping) if hasattr(r, '_mapping') else dict(r) for r in rows]


def _month_sql(engine):
  """当前月过滤:SQLite 用 strftime,MySQL 用 DATE_FORMAT。"""
  if engine.dialect.name == 'mysql':
    return "DATE_FORMAT(created_at, '%Y-%m') = DATE_FORMAT(NOW(), '%Y-%m')"
  return "strftime('%Y-%m', created_at) = strftime('%Y-%m', 'now', 'localtime')"


def monthly_board_top5(engine):
  """本月板材用量 Top5:按板材料号汇总面积(㎡)降序取前 5。"""
  with engine.connect() as conn:
    rows = conn.execute(text(
      f"""SELECT board_material AS material,
                 ROUND(SUM(length_mm * width_mm * quantity) / 1000000.0, 4) AS area_m2,
                 SUM(quantity) AS parts
          FROM bom_items
          WHERE {_month_sql(engine)}
          GROUP BY board_material
          ORDER BY area_m2 DESC
          LIMIT 5"""
    )).mappings().fetchall()
  return _rows(rows)


def avg_hardware_cost(engine):
  """单均五金成本 = 五金成本合计 ÷ 有五金入库的合规订单数。"""
  with engine.connect() as conn:
    row = conn.execute(text(
      "SELECT ROUND(SUM(cost) / COUNT(DISTINCT order_id), 2) AS avg_cost "
      "FROM hardware_items"
    )).mappings().first()
  return row['avg_cost'] if row and row['avg_cost'] is not None else 0.0


def reject_stats(engine):
  """拦截订单统计:总数 + 按违规部件/方向归因。"""
  with engine.connect() as conn:
    total = conn.execute(text('SELECT COUNT(*) AS n FROM reject_orders')).scalar_one()
    by_part = _rows(conn.execute(text(
      'SELECT part_name, COUNT(*) AS n FROM reject_orders GROUP BY part_name')).mappings().fetchall())
    by_direction = _rows(conn.execute(text(
      'SELECT direction, COUNT(*) AS n FROM reject_orders GROUP BY direction')).mappings().fetchall())
  return {'total': total, 'by_part': by_part, 'by_direction': by_direction}


def get_orders_page(engine, page=1, page_size=20):
  """订单列表分页(供 api 使用):order_id 去重, 主分页, 消息供排序。"""
  offset = max(page - 1, 0) * page_size
  with engine.connect() as conn:
    rows = conn.execute(text(
      """SELECT order_id, COUNT(DISTINCT part_name) AS part_count,
                SUM(length_mm * width_mm * quantity) / 1000000.0 AS area_m2
         FROM bom_items
         GROUP BY order_id
         ORDER BY order_id
         LIMIT :limit OFFSET :offset"""
    ), {'limit': page_size, 'offset': offset}).mappings().fetchall()
  return _rows(rows)


def get_order_bom(engine, order_id):
  """单个订单 BOM(部件+五金),供 GET /orders/{id}/bom。"""
  with engine.connect() as conn:
    parts = _rows(conn.execute(text(
      """SELECT part_name, length_mm, width_mm, board_type, board_material, quantity
         FROM bom_items WHERE order_id = :oid ORDER BY id"""
    ), {'oid': order_id}).mappings().fetchall())
    hw = _rows(conn.execute(text(
      """SELECT item_name, quantity, unit, unit_price, cost
         FROM hardware_items WHERE order_id = :oid ORDER BY id"""
    ), {'oid': order_id}).mappings().fetchall())
  return {'parts': parts, 'hardware': hw}


def get_rejects(engine):
  """全部拦截订单及原因,供 GET /alerts/rejects。"""
  with engine.connect() as conn:
    rows = _rows(conn.execute(text(
      """SELECT order_id, customer, cabinet_type, part_name, direction,
                value_mm, limit_mm, reason
         FROM reject_orders ORDER BY order_id"""
    )).mappings().fetchall())
  return rows


def get_all_order_ids(engine):
  with engine.connect() as conn:
    rows = conn.execute(text('SELECT DISTINCT order_id FROM bom_items')).scalars().all()
  return list(rows)
