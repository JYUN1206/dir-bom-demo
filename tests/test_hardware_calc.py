"""hardware_calc 测试：§5 手算五金基准 + 门高档位 + 电视柜抽屉套。"""
from src.hardware_calc import calc_hardware, to_dicts
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


def _quantities(items):
  return {item.name: (item.quantity, item.unit) for item in items}


def test_wardrobe_matches_hand_calc_hardware():
  """§5 基准:铰链 2×3=6 个、导轨 3 副、拉手 5 个、螺丝包 1 包。"""
  q = _quantities(calc_hardware(_order()))
  assert q['铰链'] == (6, '个')
  assert q['抽屉导轨'] == (3, '副')
  assert q['拉手'] == (5, '个')
  assert q['螺丝连接件包'] == (1, '包')
  assert '抽屉配件套' not in q


def test_hinge_by_door_height_tier():
  """门高>1000 每扇 3; ≤1000 每扇 2。"""
  tall = calc_hardware(_order(height_mm=2200, door_count=2))
  low = calc_hardware(_order(height_mm=900, door_count=2))
  assert _quantities(tall)['铰链'] == (6, '个')
  assert _quantities(low)['铰链'] == (4, '个')


def test_tv_cabinet_drawer_kits():
  """悬浮电视柜:无铰链、加抽屉配件套 × 抽屉数。"""
  q = _quantities(calc_hardware(_order(cabinet_type='悬浮电视柜', door_count=0,
                                       drawer_count=2, height_mm=420)))
  assert q['抽屉配件套'] == (2, '套')
  assert q['抽屉导轨'] == (2, '副')
  assert q['拉手'] == (2, '个')
  assert '铰链' not in q


def test_open_bookshelf_only_screw_pack():
  """开放书柜(无门无抽):仅螺丝包 1。"""
  q = _quantities(calc_hardware(_order(cabinet_type='书柜', door_count=0,
                                       drawer_count=0)))
  assert list(q) == ['螺丝连接件包']
  assert q['螺丝连接件包'] == (1, '包')


def test_to_dicts_shape():
  """to_dicts 输出含品名/数量/单位, 供下游使用。"""
  rows = to_dicts(calc_hardware(_order(drawer_count=0)))
  assert all(set(r) == {'name', 'quantity', 'unit'} for r in rows)
  assert {'name': '铰链', 'quantity': 6, 'unit': '个'} in rows
