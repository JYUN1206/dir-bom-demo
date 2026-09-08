"""根据 rules.md §1 把柜体订单拆成部件清单(BOM)。

个人项目 / 模拟数据 —— 简化业务模型，真实拆单规则以贵司工艺为准。
规则按「零件类型」组织而非按柜型硬编码：顶/底/侧/层/背是通用件，
门板(door_count>0 时)、电视柜抽屉面板(仅悬浮电视柜)按需追加。
尺寸约定:部件用「长 × 宽」表示，面积 = 长 × 宽 × 数量；背板薄板单列(board_type=背板)。
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import reduce

from src.parser import Order

BOARD_MAIN = '主材18mm'
BOARD_BACK = '背板9mm'

CABINET_WARDROBE = '直型衣柜'
CABINET_TV = '悬浮电视柜'

SHELF_RECESS_MM = 50  # 层板深度方向缩量(避让，见 rules.md §6-2)
DRAWER_GAP_MM = 3  # 抽屉面板间缝隙(单边)，两侧共 2×3mm


@dataclass(frozen=True, slots=True)
class BoardPart:
  """一块待开料的板件。"""

  name: str
  count: int
  length_mm: int
  width_mm: int
  board_type: str

  @property
  def area_m2(self):
    return self.length_mm * self.width_mm / 1_000_000 * self.count


def build_bom(order: Order):
  """把单个订单拆成部件清单，返回 `BoardPart` 列表。

  通用件 + 按需附加件;每种柜型的拆解见 rules.md §1。
  """
  panels = _build_panels(order)
  drawers = _build_drawer_fronts(order) if order.cabinet_type == CABINET_TV else []
  doors = _build_doors(order) if order.door_count > 0 else []
  back = _back_part(order)

  return [*panels, *drawers, *doors, back]


def _accumulate(grouped, part):
  grouped[part.board_type] = grouped.get(part.board_type, 0.0) + part.area_m2
  return grouped


def area_by_board_type(parts):
  """按板类型聚合总面积(㎡)，返回 {board_type: 面积} 字典。"""
  return reduce(_accumulate, parts, {})


def _build_panels(order):
  """顶板、底板、左/右侧板、层板——所有柜型通用。"""
  top = BoardPart('顶板', 1, order.width_mm, order.depth_mm, BOARD_MAIN)
  bottom = BoardPart('底板', 1, order.width_mm, order.depth_mm, BOARD_MAIN)
  side = BoardPart('侧板', 2, order.height_mm, order.depth_mm, BOARD_MAIN)

  if order.shelf_count <= 0:
    return [top, bottom, side]

  shelf_length = order.width_mm - SHELF_RECESS_MM
  shelf = BoardPart('层板', order.shelf_count, shelf_length, order.depth_mm, BOARD_MAIN)
  return [top, bottom, side, shelf]


def _build_doors(order):
  """门板(直型衣柜 / 书柜带门)，宽=width÷door_count,高=height。"""
  if order.door_count <= 0:
    return []
  door_length = order.width_mm // order.door_count
  return [BoardPart('门板', order.door_count, order.height_mm, door_length, BOARD_MAIN)]


def _build_drawer_fronts(order):
  """电视柜抽屉面板:数量=抽屉数,宽=(width−2×3)÷抽屉数,高=height÷抽屉数均分。"""
  if order.drawer_count <= 0:
    return []
  front_width = (order.width_mm - 2 * DRAWER_GAP_MM) // order.drawer_count
  front_length = order.height_mm // order.drawer_count
  return [BoardPart('抽屉面板', order.drawer_count, front_length, front_width, BOARD_MAIN)]


def _back_part(order):
  """背板(薄板):宽×高,单列 board_type=背板。"""
  return BoardPart('背板', 1, order.height_mm, order.width_mm, BOARD_BACK)
