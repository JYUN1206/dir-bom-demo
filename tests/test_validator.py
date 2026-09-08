"""validator 测试:两条埋雷订单被拦截且原因话术正确、合规单放行、超长优先。"""
import pytest

from src.bom_engine import build_bom
from src.parser import parse_orders
from src.validator import validate_order

DATA_ORDERS = 'data/orders.xlsx'


def _wardrobe(**overrides):
  from src.parser import Order
  base = dict(
    order_id='D0001', customer='张三', cabinet_type='直型衣柜', width_mm=1800,
    depth_mm=550, height_mm=2200, board_material='颗粒板18mm', door_count=2,
    drawer_count=3, shelf_count=4, hinge_spec='液压阻尼',
  )
  base.update(overrides)
  return Order(**base)


def _over_len(part):
  return part.length_mm > 2400


def test_planted_mine1_height_side_panel():
  """埋雷1:height=2500 → 侧板 长2500 超2400, 整单拦截, 话术正确。"""
  order = _wardrobe(height_mm=2500)
  reject = validate_order(order, build_bom(order))
  assert reject is not None
  assert reject.part_name == '侧板'
  assert (reject.direction, reject.value_mm, reject.limit_mm) == ('长', 2500, 2400)
  assert reject.reason == (
    'D0001 张三：侧板 长2500mm 超机床加工上限 2400mm，整单拦截'
  )


def test_planted_mine2_overwide_reported_as_over_length_first():
  """埋雷2:width=2500(2门)。超长优先 → 报顶板 长2500(而非门板 宽1250)。"""
  order = _wardrobe(width_mm=2500, door_count=2)
  parts = build_bom(order)
  door = next(p for p in parts if p.name == '门板')
  assert door.width_mm == 1250  # 门板确实超宽

  reject = validate_order(order, parts)
  assert reject is not None
  assert reject.part_name == '顶板'
  assert (reject.direction, reject.value_mm) == ('长', 2500)


def test_compliant_order_passes():
  """合规订单不拦截。"""
  order = _wardrobe()
  assert validate_order(order, build_bom(order)) is None


def test_end_to_end_two_mines_only(data_orders=DATA_ORDERS):
  """50 单端到端:恰好 2 条拦截 (D0001、D0017),其余 48 单合规。"""
  orders = parse_orders(data_orders)
  rejects, compliant = [], []
  for order in orders:
    reject = validate_order(order, build_bom(order))
    (rejects if reject is not None else compliant).append(order)
  assert sorted(r.order_id for r in rejects) == ['D0001', 'D0017']
  assert len(compliant) == 48
