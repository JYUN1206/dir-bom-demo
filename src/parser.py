"""读取并校验全屋定制订单 Excel，返回订单对象列表。

个人项目 / 模拟数据 —— 简化业务模型，真实拆单规则以贵司工艺为准。
尺寸字段要求为正整数，数量字段要求为非负整数；任一单元格为空或非法即整单报错，
错误信息带订单号（或 Excel 行号），便于人工定位。
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

REQUIRED_COLUMNS = (
  'order_id',
  'customer',
  'cabinet_type',
  'width_mm',
  'depth_mm',
  'height_mm',
  'board_material',
  'door_count',
  'drawer_count',
  'shelf_count',
  'hinge_spec',
  # hinge_spec 作为列必须存在（手册必填列）；但仅业务计算字段要求非空，
  # 书柜/电视柜等无五金拉手的柜型该列允许为空值。
)

OPTIONAL_COLUMNS = ()  # 保留占位：业务后续可扩展列

DIMENSION_COLUMNS = ('width_mm', 'depth_mm', 'height_mm')
COUNT_COLUMNS = ('door_count', 'drawer_count', 'shelf_count')


@dataclass(frozen=True, slots=True)
class Order:
  """一条通过校验的柜体订单。"""

  order_id: str
  customer: str
  cabinet_type: str
  width_mm: int
  depth_mm: int
  height_mm: int
  board_material: str
  door_count: int
  drawer_count: int
  shelf_count: int
  hinge_spec: str = ''


class OrderValidationError(ValueError):
  """订单数据不满足输入要求时抛出，message 含定位信息。"""


def parse_orders(input_path):
  """读取 `input_path` 指向的订单 Excel，返回按行序排列的 `Order` 列表。

  缺失必填列、空值、非法数值会在首个违规行处抛出 `OrderValidationError`。
  """
  path = Path(input_path)
  if not path.exists():
    raise FileNotFoundError(f'订单文件不存在: {path}')

  frame = pd.read_excel(path)
  _ensure_required_columns(frame)
  return [_parse_row(row, row_idx) for row_idx, row in frame.iterrows()]


def _ensure_required_columns(frame):
  missing = [c for c in REQUIRED_COLUMNS if c not in frame.columns]
  if missing:
    names = '、'.join(repr(c) for c in missing)
    raise OrderValidationError(f'缺少必填列: {names}')


def _parse_row(row, row_idx):
  raw_order_id = row['order_id']
  order_id = '' if _is_missing(raw_order_id) else str(raw_order_id).strip()
  tag = _row_tag(order_id, row_idx)

  hinge_spec = None
  if 'hinge_spec' in row.index:
    hinge_spec = row['hinge_spec']

  return Order(
    order_id=_required_text(row, 'order_id', tag),
    customer=_required_text(row, 'customer', tag),
    cabinet_type=_required_text(row, 'cabinet_type', tag),
    width_mm=_dimension(row, 'width_mm', tag),
    depth_mm=_dimension(row, 'depth_mm', tag),
    height_mm=_dimension(row, 'height_mm', tag),
    board_material=_required_text(row, 'board_material', tag),
    door_count=_count(row, 'door_count', tag),
    drawer_count=_count(row, 'drawer_count', tag),
    shelf_count=_count(row, 'shelf_count', tag),
    hinge_spec='' if _is_missing(hinge_spec) else str(hinge_spec).strip(),
  )


def _row_tag(order_id, row_idx):
  base = f'excel 第 {row_idx + 2} 行'
  return f'{base} (order_id={order_id})' if order_id else base


def _required_text(row, column, tag):
  value = row[column]
  if _is_missing(value):
    raise OrderValidationError(f'{tag}: 必填字段 {column!r} 为空')
  return str(value).strip()


def _dimension(row, column, tag):
  """尺寸字段：必须是 > 0 的整数（单位 mm）。"""
  return _integer(row, column, tag, minimum=0, exclusive=True)


def _count(row, column, tag):
  """数量字段：必须是非负整数。"""
  return _integer(row, column, tag, minimum=0, exclusive=False)


def _integer(row, column, tag, *, minimum, exclusive):
  value = row[column]
  if _is_missing(value):
    raise OrderValidationError(f'{tag}: 必填字段 {column!r} 为空')

  number = _to_number(value, column, tag)
  if number != int(number):
    raise OrderValidationError(f'{tag}: 字段 {column!r} 必须是整数，实际 {value!r}')
  number = int(number)

  valid = number > minimum if exclusive else number >= minimum
  if not valid:
    operator = '大于' if exclusive else '大于等于'
    raise OrderValidationError(
      f'{tag}: 字段 {column!r} 必须{operator} {minimum}，实际 {number}'
    )
  return number


def _to_number(value, column, tag):
  try:
    return float(value)
  except (TypeError, ValueError):
    raise OrderValidationError(f'{tag}: 字段 {column!r} 必须是数字，实际 {value!r}') from None


def _is_missing(value):
  """判定单元格是否为空（None / NaN / 空白字符串）。"""
  if value is None:
    return True
  try:
    if pd.isna(value):
      return True
  except (TypeError, ValueError):
    pass
  return isinstance(value, str) and not value.strip()
