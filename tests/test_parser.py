"""parser 模块测试：正常解析 / 空值报错 / 负数与缺列报错。"""
import pandas as pd
import pytest

from src.parser import Order, OrderValidationError, parse_orders

COLUMNS = (
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
)


@pytest.fixture
def make_file(tmp_path):
  def _make(rows, columns=COLUMNS):
    path = tmp_path / 'orders.xlsx'
    pd.DataFrame(rows, columns=columns).to_excel(path, index=False)
    return path

  return _make


def test_parse_orders_returns_valid_objects(make_file):
  rows = [
    ['D0001', '张三', '直型衣柜', 1800, 550, 2200, '颗粒板18mm', 2, 3, 4, '液压阻尼'],
    ['D0002', '李四', '悬浮电视柜', 1600, 400, 420, '多层板18mm', 0, 2, 1, ''],
  ]
  orders = parse_orders(make_file(rows))

  assert len(orders) == 2
  assert isinstance(orders[0], Order)
  assert orders[0].order_id == 'D0001'
  assert orders[0].width_mm == 1800
  assert orders[0].height_mm == 2200
  assert orders[0].door_count == 2
  assert orders[0].shelf_count == 4
  assert orders[0].hinge_spec == '液压阻尼'
  assert orders[1].drawer_count == 2
  assert orders[1].cabinet_type == '悬浮电视柜'


def test_fifty_rows_end_to_end(orders_path):
  orders = parse_orders(orders_path)
  assert len(orders) == 2


def test_empty_required_cell_raises_with_order_id(make_file):
  rows = [
    ['D0001', '张三', '直型衣柜', 1800, 550, 2200, '颗粒板18mm', 2, 3, 4, ''],
    ['D0002', '李四', '书柜', 900, None, 2100, '颗粒板18mm', 0, 0, 5, ''],
  ]
  with pytest.raises(OrderValidationError) as exc:
    parse_orders(make_file(rows))
  message = str(exc.value)
  assert 'order_id=D0002' in message
  assert 'depth_mm' in message


def test_negative_dimension_raises_with_order_id(make_file):
  rows = [['D0001', '张三', '直型衣柜', 1800, 550, -20, '颗粒板18mm', 2, 3, 4, '']]
  with pytest.raises(OrderValidationError) as exc:
    parse_orders(make_file(rows))
  message = str(exc.value)
  assert 'order_id=D0001' in message
  assert 'height_mm' in message
  assert '大于 0' in message


def test_zero_dimension_rejected(make_file):
  rows = [['D0001', '张三', '直型衣柜', 0, 550, 2200, '颗粒板18mm', 2, 3, 4, '']]
  with pytest.raises(OrderValidationError) as exc:
    parse_orders(make_file(rows))
  assert 'width_mm' in str(exc.value)


def test_negative_count_rejected(make_file):
  rows = [['D0001', '张三', '直型衣柜', 1800, 550, 2200, '颗粒板18mm', -1, 3, 4, '']]
  with pytest.raises(OrderValidationError) as exc:
    parse_orders(make_file(rows))
  assert 'door_count' in str(exc.value)


def test_missing_required_column_raises(make_file):
  columns = [c for c in COLUMNS if c != 'depth_mm']
  row = dict(zip(COLUMNS, ['D0001', '张三', '直型衣柜', 1800, 550, 2200, '颗粒板18mm', 2, 3, 4, '']))
  row = [row[c] for c in columns]
  with pytest.raises(OrderValidationError) as exc:
    parse_orders(make_file([row], columns))
  assert "'depth_mm'" in str(exc.value)


def test_file_not_found(tmp_path):
  with pytest.raises(FileNotFoundError):
    parse_orders(tmp_path / 'no_such.xlsx')
