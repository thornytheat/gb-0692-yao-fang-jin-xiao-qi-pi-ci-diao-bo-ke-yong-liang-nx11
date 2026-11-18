from datetime import date
from decimal import Decimal
from app.numeric import number
from app.errors import DomainError
AS_OF=date(2026,11,18)
def day(value):
    try: return date.fromisoformat(value)
    except ValueError: raise DomainError('DATE','日期格式无效')
def whole(value):
    n=number(value)
    if n<0 or n!=n.to_integral_value(): raise DomainError('QUANTITY','数量须为非负整数')
    return int(n)
def eligible(stock,demand):
    return stock['sku']==demand['sku'] and stock['status']=='normal' and (day(stock['expiry'])-day(demand['arrival'])).days>=demand['min_days_n'] and day(stock['expiry'])>day(demand['arrival'])
def allocate(stocks,demands):
    remaining={s.get('stock_key',s['lot']):s['available'] for s in stocks};rows=[];shortages=[]
    for d in sorted(demands,key=lambda r:(r['arrival'],r['store'],r['record'])):
        need=d['net_need'];requested=need
        for s in sorted(stocks,key=lambda r:(r['expiry'],r['lot'])):
            if not eligible(s,d): continue
            take=min(remaining[s.get('stock_key',s['lot'])],need)//s['pack_n']*s['pack_n']
            if not take: continue
            remaining[s.get('stock_key',s['lot'])]-=take;need-=take
            rows.append({'需求单':d['record'],'门店':d['store'],'药品':d['sku'],'批号':s['lot'],'到期日':s['expiry'],'调拨数量':take,'整包装':s['pack_n'],'到店余期_天':(day(s['expiry'])-day(d['arrival'])).days})
        shortages.append({'需求单':d['record'],'门店':d['store'],'净需求':requested,'已分配':requested-need,'缺口':need})
    return rows,remaining,shortages
def sellable_capacity(demand, stock, month_days=30):
    # 该批药到店后、到期前该门店预计能卖出的件数（按近三个月月均销量折算，向下取整到件）。
    sales=demand.get('sales_n')
    if sales is None: return None
    selling_days=(day(stock['expiry'])-day(demand['arrival'])).days
    return sales*selling_days//month_days
def allocate_v2(stocks, demands, month_days=30):
    """销量约束分配。
    规则：
    1) 仍只选到店余期达标且未召回的批（eligible 不变），批内按 FEFO；
    2) 每个需求单对每个批的拿货量不超过「到期前可售量」，卖不完的近效期留在中心仓；
    3) 同一药品的需求按周转（月均销量）从快到慢处理，近效期优先给周转快的门店，
       销量未知的门店排在最后并按旧规则（不设销量上限）处理；
    4) 拆包仍按整包装向下取整；缺口不改成零。
    """
    def stock_id(s): return s.get('stock_key',s['lot'])
    remaining={stock_id(s):s['available'] for s in stocks}
    fefo={d['record']:sorted((s for s in stocks if eligible(s,d)),key=lambda r:(r['expiry'],r['lot'])) for d in demands}
    def velocity(d):
        sales=d.get('sales_n')
        # 已知销量（0=已知但无周转）按周转降序优先；销量未知排最后，再按到货/门店/单号保证确定性。
        return (1 if sales is None else 0, 0 if sales is None else -sales, d['arrival'], d['store'], d['record'])
    rows=[];shortages=[]
    for d in sorted(demands,key=velocity):
        need=d['net_need'];requested=need;allocated=0
        known=d.get('sales_n') is not None
        for s in fefo[d['record']]:
            if need<=0: break
            sid=stock_id(s);on_hand=remaining[sid]
            if not on_hand: continue
            cap=sellable_capacity(d,s,month_days)
            ceiling=need if cap is None else min(need,cap)
            take=min(on_hand,ceiling)//s['pack_n']*s['pack_n']
            if not take: continue
            remaining[sid]-=take;need-=take;allocated+=take
            days=(day(s['expiry'])-day(d['arrival'])).days
            rows.append({'需求单':d['record'],'门店':d['store'],'药品':d['sku'],'批号':s['lot'],'到期日':s['expiry'],
                         '调拨数量':take,'整包装':s['pack_n'],'到店余期_天':days,
                         '月均销量':d.get('sales_n') if known else '未提供',
                         '到期前可售_件':cap if cap is not None else '未评估',
                         '预计售完':'是' if known else '销量未知'})
        if known:
            verdict='可售完' if allocated>=requested else ('部分售完' if allocated else '预计滞销未发')
        else:
            verdict='销量未知按旧规则'
        shortages.append({'需求单':d['record'],'门店':d['store'],'净需求':requested,'已分配':allocated,'缺口':need,
                          '月均销量':d.get('sales_n') if known else '未提供','预计售完':verdict})
    return rows,remaining,shortages
def near_expiry_left(stocks, remaining):
    # 留在中心仓的近效期量（效期层在 M3 已按截至日 30 天内标记）。
    rows=[]
    for s in stocks:
        if s.get('效期层')!='近效期': continue
        sid=s.get('stock_key',s['lot']);left=remaining.get(sid,0)
        rows.append({'药品':s['sku'],'批号':s['lot'],'到期日':s['expiry'],'余期_天':(day(s['expiry'])-AS_OF).days,
                     '仓内余量':left,'近效期层':'近效期'})
    return rows
