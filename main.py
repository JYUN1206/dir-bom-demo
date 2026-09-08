"""CLI 入口：串起 parser→bom_engine→hardware_calc→optimizer→validator→report→db。

个人项目 / 模拟数据 —— 简化业务模型，真实拆单规则以贵司工艺为准。
用法:
  .venv/bin/python main.py --input data/orders.xlsx --outdir output/
"""
from __future__ import annotations

import argparse
import time
from pathlib import Path

from src.bom_engine import build_bom
from src.db import avg_hardware_cost, connect, init_db, monthly_board_top5, reject_stats, save_all
from src.hardware_calc import calc_hardware
from src.optimizer import build_material_plan, load_prices, plan_cost
from src.parser import parse_orders
from src.report import OrderResult, write_reports, hardware_cost
from src.validator import validate_order


def parse_args():
  parser = argparse.ArgumentParser(description='全屋定制订单自动拆 BOM')
  parser.add_argument('--input', default='data/orders.xlsx', help='订单 Excel 路径')
  parser.add_argument('--prices', default='data/prices.xlsx', help='价格 Excel 路径')
  parser.add_argument('--outdir', default='output/', help='报表输出目录')
  parser.add_argument('--db', default='output/bom.db', help='SQLite 数据库路径')
  return parser.parse_args()


def _sum_hardware_cost(results, prices):
  return round(sum(hardware_cost(r.hardware, prices) for r in results), 2)


def run(args):
  """端到端执行, 返回状态摘要 dict。"""
  started = time.perf_counter()
  orders = parse_orders(args.input)
  prices = load_prices(args.prices)

  results, rejects = [], []
  for order in orders:
    parts = build_bom(order)
    reject = validate_order(order, parts)
    if reject is not None:
      rejects.append(reject)
    else:
      results.append(OrderResult(order, parts, calc_hardware(order),
                                 build_material_plan(order, parts, prices)))

  outdir = Path(args.outdir)
  purchase_path, reject_path = write_reports(outdir, results, rejects, prices)

  db_path = Path(args.db)
  db_path.parent.mkdir(parents=True, exist_ok=True)
  # 每次运行重建库, 保证幂等(单次流水线结果, 不累积)。
  if db_path.exists():
    db_path.unlink()
  conn = connect(db_path)
  init_db(conn)
  save_all(conn, results, rejects, prices)

  board_cost = round(sum(plan_cost(r.plan) for r in results), 2)
  hw_cost = _sum_hardware_cost(results, prices)
  summary = {
    'total': len(orders),
    'compliant': len(results),
    'rejected': len(rejects),
    'board_cost': board_cost,
    'hardware_cost': hw_cost,
    'total_cost': round(board_cost + hw_cost, 2),
    'elapsed_ms': round((time.perf_counter() - started) * 1000, 1),
    'purchase_path': str(purchase_path),
    'reject_path': str(reject_path),
    'db_path': str(db_path),
    'top5': monthly_board_top5(conn),
    'avg_hardware_cost': avg_hardware_cost(conn),
    'reject_stats': reject_stats(conn),
  }
  conn.dispose()
  return summary


def print_summary(summary):
  print('=' * 52)
  print(f'处理 {summary["total"]} 单: 合规 {summary["compliant"]} 单 / 拦截 {summary["rejected"]} 单')
  print(f'板材成本 {summary["board_cost"]} 元 + 五金成本 {summary["hardware_cost"]} 元 '
        f'= 总成本 {summary["total_cost"]} 元')
  print(f'耗时 {summary["elapsed_ms"]} ms')
  print(f'采购清单: {summary["purchase_path"]}')
  print(f'拦截清单: {summary["reject_path"]}')
  print(f'数据库: {summary["db_path"]}')
  print('本月板材用量 Top5:', [f'{t["material"]} {t["area_m2"]}㎡'
                              for t in summary['top5']])
  print('单均五金成本:', summary['avg_hardware_cost'])
  print('拦截统计:', summary['reject_stats'])
  print('=' * 52)


def main():
  args = parse_args()
  summary = run(args)
  print_summary(summary)


if __name__ == '__main__':
  main()
