from app.domain import allocate_v2, sellable_capacity, near_expiry_left
from app.pipeline import calculate
from app.config import ENGINE_V2, ENGINE_LEGACY

def _demand(record, store, sku, need, sales, arrival='2026-11-20', min_days=0):
    return {'record': record, 'store': store, 'sku': sku, 'net_need': need, 'sales_n': sales,
            'arrival': arrival, 'min_days_n': min_days}
def _stock(sku, lot, qty, expiry, pack=5, layer='近效期'):
    return {'sku': sku, 'lot': lot, 'stock_key': sku+':'+lot, 'available': qty, 'pack_n': pack,
            'expiry': expiry, 'status': 'normal', '效期层': layer}

def test_capacity_formula():
    d=_demand('D1','慢店','0001',100,6)
    s=_stock('0001','L1',100,'2026-12-15')  # 到店后 25 天
    assert sellable_capacity(d,s)==6*25//30

def test_slow_store_capped_and_near_expiry_left_in_warehouse():
    stocks=[_stock('0001','L1',100,'2026-12-15')]
    demands=[_demand('D1','慢店','0001',100,6)]
    rows,remaining,short=allocate_v2(stocks,demands)
    assert sum(r['调拨数量'] for r in rows)==5          # 可售 5 件，整包后只发 5
    assert short[0]['缺口']==95 and short[0]['预计售完']=='部分售完'
    assert remaining['0001:L1']==95
    left=near_expiry_left(stocks,remaining)
    assert left[0]['仓内余量']==95                       # 卖不完的近效期留在仓里并显式报告

def test_fast_store_gets_near_expiry_first():
    stocks=[_stock('0001','L1',50,'2026-12-15'),_stock('0001','L2',50,'2027-06-01',layer='常规')]
    demands=[_demand('D1','慢店','0001',50,6),_demand('D2','快店','0001',50,300)]
    rows,_,_=allocate_v2(stocks,demands)
    fast_lots=[r['批号'] for r in rows if r['门店']=='快店']
    assert fast_lots[0]=='L1'                            # 近效期优先给周转快的门店

def test_unknown_sales_degrades_to_legacy_rule():
    d=_demand('D1','新店','0001',50,None)
    d['sales_n']=None
    stocks=[_stock('0001','L1',50,'2026-12-15')]
    rows,_,short=allocate_v2(stocks,[d])
    assert rows[0]['预计售完']=='销量未知'
    assert short[0]['预计售完']=='销量未知按旧规则' and short[0]['缺口']==0

def test_unknown_sales_store_sorted_after_known():
    # 稀缺近效期批：已知销量的快店先拿货，销量未知的门店排在其后。
    stocks=[_stock('0001','L1',20,'2026-12-15')]
    unknown=_demand('D1','新店','0001',20,None); unknown['sales_n']=None
    fast=_demand('D2','快店','0001',20,300)
    rows,_,_=allocate_v2(stocks,[unknown,fast])
    assert rows[0]['门店']=='快店'

def test_zero_sales_keeps_everything_in_warehouse():
    stocks=[_stock('0001','L1',50,'2026-12-15')]
    rows,remaining,short=allocate_v2(stocks,[_demand('D1','冻店','0001',30,0)])
    assert not rows and remaining['0001:L1']==50
    assert short[0]['预计售完']=='预计滞销未发' and short[0]['缺口']==30

def test_whole_packages_and_deterministic(ctx):
    assert all(a['调拨数量']%a['整包装']==0 for a in ctx['allocations'])
    again=calculate()
    assert again['manifest']['run_id']==ctx['manifest']['run_id']

def test_sample_slow_stores_are_capped(ctx):
    by_record={r['需求单']:r for r in ctx['stages']['5']['shortage_rows']}
    assert by_record['D0020']['已分配']==15 and by_record['D0020']['缺口']==15

def test_engine_metrics_present(ctx):
    metrics={m[0]:m[1] for m in ctx['stages']['5']['metrics']}
    assert metrics['分配引擎']==ENGINE_V2 and '仓内近效期余量' in metrics

def test_legacy_engine_is_selectable(legacy_ctx):
    assert legacy_ctx['stages']['5']['engine']==ENGINE_LEGACY
    assert legacy_ctx['manifest']['parameters']['engine']==ENGINE_LEGACY

def test_engine_part_of_run_identity():
    a=calculate(engine='v2')['manifest']['run_id'];b=calculate(engine='legacy')['manifest']['run_id']
    assert a!=b

def test_engine_failure_falls_back_with_quarantine(monkeypatch):
    import app.modules.m5_allocation.rules as rules
    def boom(*a,**k): raise RuntimeError('boom')
    monkeypatch.setattr(rules,'allocate_v2',boom)
    result=calculate()
    assert result['stages']['5']['engine']==ENGINE_LEGACY
    assert any(q['原因码']=='ENGINE' for q in result['quarantine'])

def test_invalid_sales_is_quarantined_and_degrades(raw):
    lines=raw.splitlines()
    lines[25]=lines[25].replace(',120',',abc')
    result=calculate('\n'.join(lines)+'\n')
    assert any(q['原因码']=='SALES' for q in result['quarantine'])
    bad=next(d for d in result['net_demands'] if d['record']=='D0001')
    assert bad['sales_n'] is None
