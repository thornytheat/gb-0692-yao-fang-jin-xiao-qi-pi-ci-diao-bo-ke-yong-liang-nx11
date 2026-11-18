from app.domain import allocate
def test_allocations_whole_packages(legacy_ctx): assert all(a['调拨数量']%a['整包装']==0 for a in legacy_ctx['allocations'])
def test_fefo_first(legacy_ctx): assert legacy_ctx['allocations'][0]['到期日']=='2026-12-02'
def test_no_negative_remainder(legacy_ctx): assert min(legacy_ctx['remaining'].values())>=0
def test_demand_cap(legacy_ctx): assert all(a['已分配']<=a['净需求'] for a in legacy_ctx['shortages'])
def test_no_stock(legacy_ctx):
    rows,left,short=allocate([],legacy_ctx['net_demands']);assert not rows and sum(x['缺口'] for x in short)==735
def test_min_life_kept(legacy_ctx): assert all(a['到店余期_天']>=10 for a in legacy_ctx['allocations'])
def test_deterministic_order(legacy_ctx):
    canonical=[{k:v for k,v in a.items() if k in ('需求单','门店','药品','批号','到期日','调拨数量','整包装','到店余期_天')} for a in legacy_ctx['allocations']]
    assert allocate(list(reversed(legacy_ctx['usable'])),list(reversed(legacy_ctx['net_demands'])))[0]==canonical
