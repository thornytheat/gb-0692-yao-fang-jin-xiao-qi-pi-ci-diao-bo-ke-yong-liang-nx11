from app.domain import allocate, allocate_v2, near_expiry_left
from app.config import ENGINE_V2, ENGINE_LEGACY, default_engine, MONTH_DAYS
from app.reasons import isolate
def _run_legacy(ctx):
    rows, left, short = allocate(ctx['usable'], ctx['net_demands'])
    for r in rows:
        r.setdefault('月均销量', '未提供'); r.setdefault('到期前可售_件', '未评估'); r.setdefault('预计售完', '销量未知')
    for r in short:
        r.setdefault('月均销量', '未提供'); r.setdefault('预计售完', '销量未知按旧规则')
    return rows, left, short
def apply(ctx):
    engine = (ctx.get('engine') or default_engine()).strip().lower()
    if engine not in (ENGINE_V2, ENGINE_LEGACY): engine = default_engine()
    if engine == ENGINE_V2:
        try:
            rows, left, short = allocate_v2(ctx['usable'], ctx['net_demands'], MONTH_DAYS)
            used = ENGINE_V2
        except Exception as exc:  # 新引擎失败：保留旧版继续可用，并留下可复核证据
            isolate(ctx, {'record': 'M5', 'lot': '-', '行号': '-'}, 'ENGINE', '分配引擎异常，已回退旧版：' + type(exc).__name__)
            rows, left, short = _run_legacy(ctx); used = ENGINE_LEGACY
    else:
        rows, left, short = _run_legacy(ctx); used = ENGINE_LEGACY
    ctx.update(allocations=rows, remaining=left, shortages=short, engine=used)
    warehouse = near_expiry_left(ctx['usable'], left)
    near_left = sum(r['仓内余量'] for r in warehouse)
    return {
        'rows': rows,
        'shortage_rows': short,
        'warehouse_rows': warehouse,
        'engine': used,
        'metrics': [
            ['调拨', sum(r['调拨数量'] for r in rows), '件'],
            ['分配行', len(rows), '条'],
            ['缺口', sum(r['缺口'] for r in short), '件'],
            ['仓内近效期余量', near_left, '件'],
            ['分配引擎', used, ''],
        ],
    }
