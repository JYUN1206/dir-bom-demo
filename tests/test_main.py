"""main 端到端测试：跑 run() 校验汇总与产出文件。用 tmp_path 隔离输出。"""
import argparse
import importlib
from pathlib import Path

from src.parser import parse_orders

DATA = Path('data/orders.xlsx').resolve()
PRICES = Path('data/prices.xlsx').resolve()


def _args(tmp_path):
  return argparse.Namespace(
    input=str(DATA), prices=str(PRICES),
    outdir=str(tmp_path / 'out'), db=str(tmp_path / 'bom.db'),
  )


def test_run_pipeline_end_to_end(tmp_path):
  main = importlib.import_module('main')
  summary = main.run(_args(tmp_path))

  assert summary['total'] == 50
  assert summary['compliant'] == 48
  assert summary['rejected'] == 2
  assert summary['total_cost'] == 51830.0
  assert Path(summary['purchase_path']).exists()
  assert Path(summary['reject_path']).exists()
  assert Path(summary['db_path']).exists()
  assert summary['reject_stats']['total'] == 2
  assert len(summary['top5']) >= 1


def test_main_input_matches_parser(tmp_path):
  main = importlib.import_module('main')
  orders = parse_orders(str(DATA))
  summary = main.run(_args(tmp_path))
  assert len(orders) == summary['total']
