"""验证每次运行重建 SQLite 库, 连续两次统计结果一致(不累积)。"""
import argparse
import importlib
from pathlib import Path

from src.db import connect, reject_stats

DATA = Path('data/orders.xlsx').resolve()
PRICES = Path('data/prices.xlsx').resolve()


def _run(tmp_path):
  main = importlib.import_module('main')
  return main.run(argparse.Namespace(
    input=str(DATA), prices=str(PRICES),
    outdir=str(tmp_path / 'out'), db=str(tmp_path / 'bom.db'),
  ))


def test_rerun_is_idempotent(tmp_path):
  first = _run(tmp_path)
  second = _run(tmp_path)
  assert first['rejected'] == second['rejected'] == 2
  assert first['total_cost'] == second['total_cost']
