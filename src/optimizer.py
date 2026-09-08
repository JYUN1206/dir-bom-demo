"""根据 rules.md §3 算料:主材/背板分开聚合,×1.08 损耗,÷2.9768向上取整,并算成本。

个人项目 / 模拟数据 —— 简化业务模型，真实拆单规则以贵司工艺为准。
标准板单张面积 2440×1220 = 2.9768㎡(手册"4.93㎡"系旧笔误,统一用 2.9768)。
输入部件清单 + 价格表,输出料单(板种/规格/张数/单价/成本)。
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from src.bom_engine import BOARD_BACK, BOARD_MAIN
from src.parser import Order

SHEET_AREA_M2 = 2.9768
LOSS_FACTOR = 1.08

PRICE_BACK_ITEM = '板材-背板9mm'


@dataclass(frozen=True, slots=True)
class MaterialLine:
  """一类板材的算料结果。"""

  category: str  # 主材 / 背板
  board_type: str  # 对应 bom_engine 的 BOARD_MAIN / BOARD_BACK
  material: str  # 具体板名, 如 颗粒板18mm
  area_m2: float  # 原始面积合计
  required_m2: float  # 含损耗需求面积
  sheets: int  # 标准张数(向上取整)
  unit_price: float
  cost: float  # sheets × unit_price


def load_prices(path):
  """读 prices.xlsx, 返回 {item: {'unit': ..., 'price': ...}}。"""
  frame = pd.read_excel(path)
  return {
    row['item']: {'unit': row['unit'], 'price': float(row['unit_price'])}
    for row in frame.to_dict(orient='records')
  }


def required_area(area_m2):
  return round(area_m2 * LOSS_FACTOR, 4)


def sheets_for(area_m2):
  return math.ceil(area_m2 / SHEET_AREA_M2)


def build_material_plan(order: Order, parts, prices):
  """为一个订单算料, 返回 `MaterialLine` 列表(主材在前,背板在后)。"""
  main_area = sum(p.area_m2 for p in parts if p.board_type == BOARD_MAIN)
  back_area = sum(p.area_m2 for p in parts if p.board_type == BOARD_BACK)

  main_material = order.board_material
  main_item = f'板材-{main_material}'
  main_price = prices[main_item]['price']
  back_price = prices[PRICE_BACK_ITEM]['price']

  main = _line('主材', BOARD_MAIN, main_material, main_area, main_price)
  back = _line('背板', BOARD_BACK, '背板9mm', back_area, back_price)
  return [main, back]


def _line(category, board_type, material, area_m2, unit_price):
  required = required_area(area_m2)
  sheets = sheets_for(required)
  return MaterialLine(
    category=category,
    board_type=board_type,
    material=material,
    area_m2=round(area_m2, 4),
    required_m2=required,
    sheets=sheets,
    unit_price=unit_price,
    cost=round(sheets * unit_price, 2),
  )


def plan_cost(lines):
  """料单成本合计。"""
  return round(sum(line.cost for line in lines), 2)
