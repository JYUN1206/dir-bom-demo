"""生成演示用模拟数据：data/orders.xlsx + data/prices.xlsx。

个人项目 / 模拟数据。50 行订单覆盖 3 种柜型、2 种板材，并埋 2 条工艺违规：
  - D0001 height_mm=2500（侧板超长 >2400）
  - D0017 width_mm=2500 且 2 门（门板宽 1250 >1200）
"""
from __future__ import annotations

from pathlib import Path

from openpyxl import Workbook

SHEET = Path(__file__).resolve().parent.parent / 'data'
HEADERS = (
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

CABINETS = {
  '直型衣柜': dict(depth_mm=550, height_mm=2200, door_count=2, drawer_count=3, shelf_count=4),
  '悬浮电视柜': dict(depth_mm=400, height_mm=420, door_count=0, drawer_count=2, shelf_count=1),
  '书柜': dict(depth_mm=300, height_mm=2100, door_count=0, drawer_count=0, shelf_count=5),
}
MATERIALS = ('颗粒板18mm', '多层板18mm')


def _cabinet_width(cabinet_type, idx):
  if cabinet_type == '直型衣柜':
    return 1600 + (idx % 4) * 200
  if cabinet_type == '悬浮电视柜':
    return 1600 + (idx % 4) * 200
  return 800 + (idx % 5) * 200


def build_orders():
  rows = []
  for idx in range(1, 51):
    cabinet_type = ('直型衣柜', '悬浮电视柜', '书柜')[idx % 3]
    profile = CABINETS[cabinet_type]
    material = MATERIALS[idx % 2]

    order_id = f'D{idx:04d}'
    width = _cabinet_width(cabinet_type, idx)
    height = profile['height_mm']

    # 埋雷 1：第 1 单强制直型衣柜(深550)，侧板 550×2500 超长 >2400
    if idx == 1:
      cabinet_type = '直型衣柜'
      profile = CABINETS[cabinet_type]
      height = 2500
    # 埋雷 2：第 17 单直型衣柜宽 2500，2 门 → 门板宽 1250 >1200（同时顶/底板 2500 超长）
    if idx == 17:
      cabinet_type = '直型衣柜'
      profile = CABINETS[cabinet_type]
      width = 2500

    rows.append(
      {
        'order_id': order_id,
        'customer': f'客户{idx:02d}',
        'cabinet_type': cabinet_type,
        'width_mm': width,
        'depth_mm': profile['depth_mm'],
        'height_mm': height,
        'board_material': material,
        'door_count': profile['door_count'],
        'drawer_count': profile['drawer_count'],
        'shelf_count': profile['shelf_count'],
        'hinge_spec': '液压阻尼' if cabinet_type == '直型衣柜' else '',
      }
    )
  return rows


def build_prices():
  return [
    ('板材-颗粒板18mm', '主材', '张', 220),
    ('板材-多层板18mm', '主材', '张', 260),
    ('板材-背板9mm', '背板', '张', 145),
    ('铰链', '五金', '个', 8.5),
    ('抽屉导轨', '五金', '副', 25),
    ('拉手', '五金', '个', 12),
    ('螺丝连接件包', '五金', '包', 30),
    ('抽屉配件套', '五金', '套', 45),
  ]


def _write_sheet(book, title, header, rows):
  sheet = book.active
  sheet.title = title
  sheet.append(header)
  for row in rows:
    sheet.append([row.get(c) for c in header])


def main():
  SHEET.mkdir(parents=True, exist_ok=True)

  orders = Workbook()
  _write_sheet(orders, 'orders', list(HEADERS), build_orders())
  orders.save(SHEET / 'orders.xlsx')

  prices = Workbook()
  price_headers = ('item', 'category', 'unit', 'unit_price')
  price_rows = [
    {'item': item, 'category': cat, 'unit': unit, 'unit_price': price}
    for item, cat, unit, price in build_prices()
  ]
  _write_sheet(prices, 'prices', price_headers, price_rows)
  prices.save(SHEET / 'prices.xlsx')

  print(f'生成完成: {SHEET / "orders.xlsx"}（{len(build_orders())} 行）, {SHEET / "prices.xlsx"}')
  print('埋雷订单: D0001 height_mm=2500 | D0017 width_mm=2500(2门)')


if __name__ == '__main__':
  main()
