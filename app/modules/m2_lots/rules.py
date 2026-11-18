from app.domain import whole,day
from app.errors import DomainError
from app.reasons import isolate
from app.numeric import number
def parse_sales(ctx, r):
    # 月均销量为可选字段：库存行不使用；需求行缺失记 None（后续按旧规则降级），脏值隔离后同样降级。
    raw=(r.get('monthly_sales') or '').strip()
    if not raw: return None
    try:
        value=number(raw)
        if value<0 or value!=value.to_integral_value(): raise DomainError('SALES','月均销量须为非负整数')
        return int(value)
    except DomainError:
        isolate(ctx,r,'SALES','月均销量无效，销量约束降级')
        return None
def apply(ctx):
    stocks=[];demands=[];seen={};duplicates=0
    for r in ctx['rows']:
        try:
            if r['kind'] not in ('stock','demand'): raise DomainError('KIND','记录类别无效')
            qty=whole(r['qty']);frozen=whole(r['frozen']);pack=whole(r['pack']);days=whole(r['min_days'])
            if (r['kind']=='stock' and frozen>qty) or pack<1: raise DomainError('QUANTITY','冻结量或包装数量无效')
            if not r['sku'] or not r['record']: raise DomainError('MISSING','业务编号为空')
            if r['version']!='1': raise DomainError('VERSION','来源版本不支持')
            day(r['arrival'])
            if r['kind']=='stock':
                day(r['expiry'])
                if not r['lot']: raise DomainError('MISSING','批号为空')
            key=(r['kind'],r['record']);fingerprint=tuple((k,v) for k,v in r.items() if k!='行号')
            if key in seen:
                if seen[key]==fingerprint: duplicates+=1
                else: isolate(ctx,r,'CONFLICT','来源单号内容冲突')
                continue
            seen[key]=fingerprint
            item={**r,'qty_n':qty,'frozen_n':frozen,'pack_n':pack,'min_days_n':days}
            if r['kind']=='demand': item['sales_n']=parse_sales(ctx,r)
            (stocks if r['kind']=='stock' else demands).append(item)
        except DomainError as e: isolate(ctx,r,e.code,e.message)
    # Recall is dominant even when a normal copy appeared earlier.
    recalls={(r['sku'],r['lot']) for r in ctx['rows'] if r['kind']=='stock' and r['status']=='recall'}
    unique={};valid=[]
    for s in stocks:
        if (s['sku'],s['lot']) in recalls: isolate(ctx,s,'RECALL','召回批禁止调拨');continue
        if (s['sku'],s['lot']) in unique: isolate(ctx,s,'LOT_DUP','批号重复来源');continue
        s['stock_key']=s['sku']+':'+s['lot'];unique[(s['sku'],s['lot'])]=s;valid.append(s)
    ctx.update(stocks=valid,demands=demands,duplicates=duplicates)
    return {'rows':valid+demands,'metrics':[['有效库存',len(valid),'批'],['门店需求',len(demands),'单'],['隔离',len(ctx['quarantine']),'条']]}

