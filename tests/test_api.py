"""api 测试:四接口 + 404 + 分页。用内存 SQLite + FastAPI TestClient。"""
import importlib
import sys

import pytest
from fastapi.testclient import TestClient

from src import api as api_module
from src.bom_engine import build_bom
from src.db import init_db, save_all
from src.hardware_calc import calc_hardware
from src.optimizer import build_material_plan, load_prices
from src.parser import Order
from src.report import OrderResult
from src.validator import RejectRecord

PRICES = load_prices('data/prices.xlsx')


def _order(order_id='D0001'):
  return Order(order_id=order_id, customer='张三', cabinet_type='直型衣柜',
               width_mm=1800, depth_mm=550, height_mm=2200,
               board_material='颗粒板18mm', door_count=2, drawer_count=3,
               shelf_count=4, hinge_spec='液压阻尼')


def _result(order):
  return OrderResult(order=order, parts=build_bom(order),
                     hardware=calc_hardware(order),
                     plan=build_material_plan(order, build_bom(order), PRICES))


@pytest.fixture
def client(monkeypatch):
  # 用一个内存 SQLite, 绕过真实文件, 并把 api.get_engine 指向它
  engine = api_module.connect(override='sqlite:///:memory:')
  init_db(engine)
  save_all(engine, [_result(_order()), _result(_order('D0002'))], [
    RejectRecord('D0001', '张三', '直型衣柜', '侧板', '长', 2500, 2400),
  ], PRICES)
  monkeypatch.setattr(api_module, 'get_engine', lambda: engine)
  return TestClient(api_module.app)


def test_health(client):
  assert client.get('/health').json()['status'] == 'ok'


def test_list_orders_paginated(client):
  resp = client.get('/orders')
  assert resp.status_code == 200
  data = resp.json()
  assert data['total'] == 2
  assert len(data['items']) == 2


def test_page_size_validation(client):
  assert client.get('/orders?page=0').status_code == 422
  assert client.get('/orders?page_size=500').status_code == 422


def test_order_bom(client):
  resp = client.get('/orders/D0001/bom')
  assert resp.status_code == 200
  data = resp.json()
  assert len(data['parts']) == len(build_bom(_order()))
  assert data['hardware_cost'] == 216.0  # 6*8.5+3*25+5*12+1*30


def test_order_bom_404(client):
  resp = client.get('/orders/NO_SUCH/bom')
  assert resp.status_code == 404
  assert '不存在' in resp.json()['detail']


def test_stats_monthly(client):
  resp = client.get('/stats/monthly')
  assert resp.status_code == 200
  data = resp.json()
  assert 'board_top5' in data and 'avg_hardware_cost' in data
  assert data['avg_hardware_cost'] == 216.0


def test_alerts_rejects(client):
  resp = client.get('/alerts/rejects')
  assert resp.status_code == 200
  data = resp.json()
  assert len(data['rejects']) == 1
  assert '侧板 长2500mm 超机床加工上限 2400mm' in data['rejects'][0]['reason']
