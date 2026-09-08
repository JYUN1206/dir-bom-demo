"""db 测试(SQLAlchemy 版):建表、入库、3 条统计。用内存 SQLite 无需真实库。"""
import pytest
from sqlalchemy import text

from src.bom_engine import build_bom
from src.db import (
  avg_hardware_cost,
  connect,
  get_order_bom,
  get_orders_page,
  get_rejects,
  init_db,
  insert_reject,
  monthly_board_top5,
  reject_stats,
  save_all,
)
from src.hardware_calc import calc_hardware
from src.optimizer import build_material_plan, load_prices
from src.parser import Order
from src.report import OrderResult
from src.validator import RejectRecord

PRICES = load_prices('data/prices.xlsx')


@pytest.fixture
def engine():
  eng = connect(override='sqlite:///:memory:')
  init_db(eng)
  yield eng
  eng.dispose()


def _order(**overrides):
  base = dict(
    order_id='D0001', customer='张三', cabinet_type='直型衣柜', width_mm=1800,
    depth_mm=550, height_mm=2200, board_material='颗粒板18mm', door_count=2,
    drawer_count=3, shelf_count=4, hinge_spec='液压阻尼',
  )
  base.update(overrides)
  return Order(**base)


def _result(order=None):
  order = order or _order()
  return OrderResult(order=order, parts=build_bom(order),
                     hardware=calc_hardware(order),
                     plan=build_material_plan(order, build_bom(order), PRICES))


def _count(engine, table):
  with engine.connect() as conn:
    return conn.execute(text(f'SELECT COUNT(*) FROM {table}')).scalar_one()


def test_init_creates_tables(engine):
  with engine.connect() as conn:
    names = {r[0] for r in conn.execute(text(
      "SELECT name FROM sqlite_master WHERE type='table'"))}
  assert {'bom_items', 'hardware_items', 'reject_orders'} <= names


def test_save_all_inserts_rows(engine):
  order = _order()
  save_all(engine, [_result(order)], [], PRICES)
  assert _count(engine, 'bom_items') == len(build_bom(order))  # 6 部件
  assert _count(engine, 'hardware_items') == 4  # 铰链/导轨/拉手/螺丝包


def test_monthly_board_top5(engine):
  save_all(engine, [_result(_order()),
                    _result(_order(order_id='D0002', board_material='多层板18mm'))], [], PRICES)
  top = monthly_board_top5(engine)
  assert len(top) >= 2
  assert top[0]['area_m2'] >= top[1]['area_m2']


def test_avg_hardware_cost(engine):
  save_all(engine, [_result(_order())], [], PRICES)
  assert avg_hardware_cost(engine) == 216.0  # 6*8.5+3*25+5*12+1*30


def test_reject_stats(engine):
  insert_reject(engine, RejectRecord('D0001', '张三', '直型衣柜', '侧板', '长', 2500, 2400))
  insert_reject(engine, RejectRecord('D0017', '客户17', '直型衣柜', '顶板', '长', 2500, 2400))
  stats = reject_stats(engine)
  assert stats['total'] == 2
  assert sum(d['n'] for d in stats['by_part']) == 2
  assert stats['by_direction'][0]['direction'] == '长'


def test_get_order_bom_and_rejects(engine):
  save_all(engine, [_result(_order())], [], PRICES)
  insert_reject(engine, RejectRecord('D0001', '张三', '直型衣柜', '侧板', '长', 2500, 2400))
  bom = get_order_bom(engine, 'D0001')
  assert len(bom['parts']) == len(build_bom(_order()))
  assert len(bom['hardware']) == 4
  assert get_rejects(engine)[0]['reason'].startswith('D0001')


def test_get_orders_page(engine):
  save_all(engine, [_result(_order()), _result(_order(order_id='D0002'))], [], PRICES)
  page = get_orders_page(engine, page=1, page_size=20)
  assert {r['order_id'] for r in page} == {'D0001', 'D0002'}
