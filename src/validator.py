"""工艺校验:任一部件的长/宽超标准板净裁面则整单拦截(rules.md §4)。

个人项目 / 模拟数据 —— 简化业务模型，真实拆单规则以贵司工艺为准。
母规则:零件任一维 ≤ 净裁面。超限整单拦截(不放行单部件, 见 rules.md §6-7)。
同一订单多违规时「超长优先于超宽」, 同维度取 BOM 中第一个违规件, 报唯一原因话术。
"""
from __future__ import annotations

from dataclasses import dataclass

from src.bom_engine import BOARD_BACK
from src.parser import Order

LIMIT_LENGTH_MM = 2400
LIMIT_WIDTH_MM = 1200


@dataclass(frozen=True, slots=True)
class RejectRecord:
  """一条被整单拦截的订单及其原因。"""

  order_id: str
  customer: str
  cabinet_type: str
  part_name: str
  direction: str  # 长 / 宽
  value_mm: int
  limit_mm: int

  @property
  def reason(self):
    return (
      f'{self.order_id} {self.customer}：{self.part_name} '
      f'{self.direction}{self.value_mm}mm 超机床加工上限 {self.limit_mm}mm，整单拦截'
    )

  def to_dict(self):
    return {
      'order_id': self.order_id,
      'customer': self.customer,
      'cabinet_type': self.cabinet_type,
      'part_name': self.part_name,
      'direction': self.direction,
      'value_mm': self.value_mm,
      'limit_mm': self.limit_mm,
      'reason': self.reason,
    }


def _first_violation(parts):
  """返回 (部件, 方向, 实际值, 上限): 超长优先, 同维度取第一个。

  背板(9mm 薄板)豁免——实际按竖条拼接/分块下料, 不适用单块净裁限制(rules.md §4)。
  """
  long_one = None
  wide_one = None
  for part in parts:
    if part.board_type == BOARD_BACK:
      continue
    if part.length_mm > LIMIT_LENGTH_MM and long_one is None:
      long_one = (part, '长', part.length_mm, LIMIT_LENGTH_MM)
    elif part.width_mm > LIMIT_WIDTH_MM and wide_one is None:
      wide_one = (part, '宽', part.width_mm, LIMIT_WIDTH_MM)
  return long_one or wide_one


def validate_order(order: Order, parts):
  """单个订单校验, 通过返回 None, 违规返回 `RejectRecord`。"""
  violation = _first_violation(parts)
  if violation is None:
    return None
  part, direction, value, limit = violation
  return RejectRecord(
    order_id=order.order_id,
    customer=order.customer,
    cabinet_type=order.cabinet_type,
    part_name=part.name,
    direction=direction,
    value_mm=value,
    limit_mm=limit,
  )
