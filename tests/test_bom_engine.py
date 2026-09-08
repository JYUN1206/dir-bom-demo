"""bom_engine 测试：以 rules.md §5 手算基准单(直型衣柜)为断言核心，
另覆盖电视柜抽屉面板、书柜无门、门板复用、面积聚合。"""
import pytest

from src.bom_engine import (
  BOARD_BACK,
  BOARD_MAIN,
  build_bom,
  area_by_board_type,
)
from src.parser import Order


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


def test_wardrobe_matches_hand_calc_baseline():
  """直型衣柜 1800×550×2200、2门3抽4层 —— 逐件核对 rules.md §5 基准。"""
  parts = build_bom(_order())

  by_name = {part.name: part for part in parts}

  assert [p.name for p in parts if p.name == '顶板'] == ['顶板']
  assert by_name['顶板'].count == 1
  assert (by_name['顶板'].length_mm, by_name['顶板'].width_mm) == (1800, 550)

  assert by_name['底板'].count == 1
  assert (by_name['底板'].length_mm, by_name['底板'].width_mm) == (1800, 550)

  side = by_name['侧板']
  assert side.count == 2
  assert (side.length_mm, side.width_mm) == (2200, 550)

  shelf = by_name['层板']
  assert shelf.count == 4
  assert (shelf.length_mm, shelf.width_mm) == (1750, 550)  # 1800-50

  door = by_name['门板']
  assert door.count == 2
  assert (door.length_mm, door.width_mm) == (2200, 900)  # 1800÷2

  back = by_name['背板']
  assert back.count == 1
  assert (back.length_mm, back.width_mm) == (2200, 1800)
  assert back.board_type == BOARD_BACK

  # 所有主材件都应是主材
  assert {p.board_type for p in parts if p.name != '背板'} == {BOARD_MAIN}


def test_wardrobe_areas_match_hand_calc():
  """§5 手算:主材 12.21㎡、背板 3.96㎡。"""
  areas = area_by_board_type(build_bom(_order()))
  assert round(areas[BOARD_MAIN], 2) == 12.21
  assert round(areas[BOARD_BACK], 2) == 3.96


def test_tv_cabinet_drawer_fronts_only():
  """悬浮电视柜:无门板、有抽屉面板,面板宽=(1600−6)÷2=797、高=420÷2=210。"""
  order = _order(cabinet_type='悬浮电视柜', width_mm=1600, height_mm=420,
                 door_count=0, drawer_count=2, shelf_count=1)
  names = [p.name for p in build_bom(order)]

  assert '门板' not in names
  fronts = [p for p in build_bom(order) if p.name == '抽屉面板']
  assert len(fronts) == 1
  front = fronts[0]
  assert front.count == 2
  assert (front.length_mm, front.width_mm) == (210, 797)
  assert front.board_type == BOARD_MAIN


def test_bookshelf_open_no_doors():
  """书柜默认无门;带门时门板同衣柜算法(长=height、宽=width÷door)。"""
  open_order = _order(cabinet_type='书柜', door_count=0, drawer_count=0)
  assert '门板' not in [p.name for p in build_bom(open_order)]

  glazed = _order(cabinet_type='书柜', door_count=2, drawer_count=0, width_mm=1200)
  doors = [p for p in build_bom(glazed) if p.name == '门板']
  assert doors[0].count == 2
  assert (doors[0].length_mm, doors[0].width_mm) == (2200, 600)


def test_no_shelf_count_skips_shelves():
  """shelf_count=0 时不产生层板,其余件仍在。"""
  parts = build_bom(_order(shelf_count=0))
  assert '层板' not in [p.name for p in parts]
  assert any(p.name == '侧板' for p in parts)
