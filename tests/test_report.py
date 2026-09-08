"""report 测试:文件生成且可读、成本合计与手算一致、reject 含原因列。"""
import pytest

from src.bom_engine import build_bom
from src.hardware_calc import calc_hardware
from src.optimizer import build_material_plan, load_prices
from src.parser import Order
from src.report import (
  OrderResult,
  build_purchase_workbook,
  build_reject_workbook,
  readable,
  totals,
  write_reports,
)
from src.validator import RejectRecord

PRICES = load_prices('data/prices.xlsx')


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


def test_totals_match_hand_calc():
  """成本合计:板材 5×220+2×145=1390; 五金 6×8.5+3×25+5×12+1×30=216; 总计 1606。"""
  board_cost, hw_cost, total = totals(_result(), PRICES)
  assert board_cost == 1390
  assert hw_cost == 216
  assert total == 1606


def test_write_reports_creates_readable_files(tmp_path):
  result = _result()
  reject = RejectRecord('D0001', '张三', '直型衣柜', '侧板', '长', 2500, 2400)
  purchase, reject_file = write_reports(tmp_path, [result], [reject], PRICES)
  assert purchase.exists() and purchase.name == 'purchase_list.xlsx'
  assert reject_file.exists() and reject_file.name == 'reject_list.xlsx'
  assert readable(purchase)
  assert readable(reject_file)


def test_purchase_workbook_sheets_and_row():
  """采购清单含 板材/五金/汇总 三页,汇总行成本正确。"""
  book = build_purchase_workbook([_result()], PRICES)
  assert book.sheetnames == ['板材', '五金', '汇总']
  summary = list(book['汇总'].iter_rows(values_only=True))
  assert summary[1][-1] == 1606  # 第一单总成本


def test_reject_workbook_has_reason_column():
  """reject 清单表头含原因列且值正确。"""
  reject = RejectRecord('D0017', '客户17', '直型衣柜', '顶板', '长', 2500, 2400)
  book = build_reject_workbook([reject])
  sheet = book['reject']
  headers = [c.value for c in sheet[1]]
  assert '原因' in headers
  assert sheet.max_row == 2
  reason = sheet.cell(row=2, column=headers.index('原因') + 1).value
  assert ('顶板 长2500mm 超机床加工上限 2400mm，整单拦截' in reason)
