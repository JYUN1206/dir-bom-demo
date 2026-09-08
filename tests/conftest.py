"""共享 fixture：构造一份可通过校验的订单 Excel。"""
import pandas as pd
import pytest
from openpyxl import Workbook


@pytest.fixture
def orders_path(tmp_path):
  rows = [
    {
      'order_id': 'D0001',
      'customer': '张三',
      'cabinet_type': '直型衣柜',
      'width_mm': 1800,
      'depth_mm': 550,
      'height_mm': 2200,
      'board_material': '颗粒板18mm',
      'door_count': 2,
      'drawer_count': 3,
      'shelf_count': 4,
      'hinge_spec': '液压阻尼',
    },
    {
      'order_id': 'D0002',
      'customer': '李四',
      'cabinet_type': '悬浮电视柜',
      'width_mm': 1600,
      'depth_mm': 400,
      'height_mm': 420,
      'board_material': '多层板18mm',
      'door_count': 0,
      'drawer_count': 2,
      'shelf_count': 1,
      'hinge_spec': '',
    },
  ]
  path = tmp_path / 'orders.xlsx'
  frame = pd.DataFrame(rows)
  frame.to_excel(path, index=False)
  return path


def write_custom(rows, columns, path):
  book = Workbook()
  sheet = book.create_sheet('orders', 0)
  sheet.append(list(columns))
  for row in rows:
    sheet.append(row)
  book.remove(book['Sheet'])
  book.save(path)
  return path
