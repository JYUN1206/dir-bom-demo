"""optimizer 测试：§5 手算基准(主材5张/背板2张)、损耗、ceil 边界、主背分离。"""
import pytest

from src.bom_engine import build_bom
from src.optimizer import (
  SHEET_AREA_M2,
  build_material_plan,
  load_prices,
  required_area,
  sheets_for,
)
from src.parser import Order

PRICES_PATH = 'data/prices.xlsx'


def _order(**overrides):
  base = dict(
    order_id='D0001',
    customer='张三',
    cabinet_type='直型衣柜',
    width_mm=1800,
    depth_mm=550,
    height_mm=2200,
    board_material='颗粒板18mm',
    door_count=2,
    drawer_count=3,
    shelf_count=4,
    hinge_spec='液压阻尼',
  )
  base.update(overrides)
  return Order(**base)


@pytest.fixture(scope='module')
def prices():
  return load_prices(PRICES_PATH)


def test_wardrobe_hand_calc_sheets(prices):
  """§5 基准:1800×550×2200、2门3抽4层 → 主材 5 张、背板 2 张。"""
  plan = build_material_plan(_order(), build_bom(_order()), prices)
  main, back = plan
  assert (main.category, main.sheets) == ('主材', 5)
  assert (back.category, back.sheets) == ('背板', 2)


def test_required_area_and_sheets_rounding():
  """损耗=×1.08; 张数=ceil(面积÷2.9768)。"""
  assert required_area(12.21) == 13.1868  # §5 手算
  assert sheets_for(13.1868) == 5
  assert sheets_for(required_area(3.96)) == 2


def test_sheet_boundary_ceil():
  """恰好整除也向上取整为整数张。"""
  assert sheets_for(SHEET_AREA_M2) == 1
  assert sheets_for(SHEET_AREA_M2 - 0.0001) == 1
  assert sheets_for(1) == 1


def test_boards_separated_by_type(prices):
  """主材与背板必须分开成两行。"""
  plan = build_material_plan(_order(), build_bom(_order()), prices)
  assert [line.board_type for line in plan] == ['主材18mm', '背板9mm']


def test_material_price_by_board(prices):
  """主材价格随 board_material(颗粒板220 / 多层板260)。"""
  particle = build_material_plan(
    _order(board_material='颗粒板18mm'), build_bom(_order()), prices
  )[0]
  multi = build_material_plan(
    _order(board_material='多层板18mm'), build_bom(_order()), prices
  )[0]
  assert particle.unit_price == 220
  assert multi.unit_price == 260


def test_plan_cost_sum(prices):
  """成本=Σ补张×单价(主材 5×220 + 背板 2×145 = 1390)。"""
  plan = build_material_plan(_order(), build_bom(_order()), prices)
  boards_cost = plan[0].cost + plan[1].cost
  assert boards_cost == 5 * 220 + 2 * 145
  assert plan[0].cost == 1100
  assert plan[1].cost == 290
