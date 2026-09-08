"""根据 rules.md §2 计算每单五金清单(品名/数量/单位)。

个人项目 / 模拟数据 —— 简化业务模型，真实拆单规则以贵司工艺为准。
铰链按门高档位(>1000mm 每扇 3,否则 2)；抽屉导轨、拉手按数量；
每柜 1 包螺丝连接件；悬浮电视柜额外按抽屉数配抽屉配件套(外购抽盒口径)。
本模块只算数量，单价由 optimizer/report 结合 prices.xlsx 计算。
"""
from __future__ import annotations

from dataclasses import dataclass

from src.parser import Order

HINGE_THRESHOLD_MM = 1000
CABINET_TV = '悬浮电视柜'


@dataclass(frozen=True, slots=True)
class HardwareItem:
  """一种五金件及其数量、计量单位。"""

  name: str
  quantity: int
  unit: str


def calc_hardware(order: Order):
  """返回某订单的五金清单 `HardwareItem` 列表。"""
  hinges = _hinges(order)
  slide = _drawer_slides(order)
  handles = _handles(order)
  screw = _screw_pack(order)
  drawer_kit = _drawer_kits(order)
  return [*hinges, *slide, *handles, *screw, *drawer_kit]


def _hinges(order):
  """铰链 = 门扇数 × (门高>1000mm 取 3,否则 2)。"""
  if order.door_count <= 0:
    return []
  per_door = 3 if order.height_mm > HINGE_THRESHOLD_MM else 2
  return [HardwareItem('铰链', order.door_count * per_door, '个')]


def _drawer_slides(order):
  """抽屉导轨 = 抽屉数 × 1 副。"""
  if order.drawer_count <= 0:
    return []
  return [HardwareItem('抽屉导轨', order.drawer_count, '副')]


def _handles(order):
  """拉手 = 门扇数 + 抽屉数,每扇/每抽 1 个。"""
  total = order.door_count + order.drawer_count
  if total <= 0:
    return []
  return [HardwareItem('拉手', total, '个')]


def _screw_pack(order):
  """螺丝连接件包 = 每柜 1 包(简化口径)。"""
  return [HardwareItem('螺丝连接件包', 1, '包')]


def _drawer_kits(order):
  """抽屉配件套(仅悬浮电视柜)= 抽屉数 × 1 套, 外购抽盒口径。"""
  if order.cabinet_type != CABINET_TV or order.drawer_count <= 0:
    return []
  return [HardwareItem('抽屉配件套', order.drawer_count, '套')]


def to_dicts(items):
  """把五金清单转成 [{品名/数量/单位}] 字典列表, 便于输出/入库。"""
  return [
    {'name': item.name, 'quantity': item.quantity, 'unit': item.unit}
    for item in items
  ]
