from app.pipeline import calculate
import pytest
from app.errors import DomainError
def test_sample_records(ctx): assert ctx['input_count']==49
def test_sample_stock(ctx): assert ctx['stages']['1']['metrics'][0][1]==29
def test_bom(raw): # TRAP-02
    assert calculate('﻿'+raw)['input_count']==49
def test_bad_columns(raw): # TRAP-05
    assert any(r['原因码']=='COLUMNS' for r in calculate(raw+'bad,row\n')['quarantine'])
def test_no_rows(raw):
    with pytest.raises(DomainError): calculate(raw.splitlines()[0])
def test_record_id_preserved(ctx): assert ctx['rows'][0]['record']=='S0001'
def test_column_order(raw):
    import csv,io
    rs=list(csv.reader(io.StringIO(raw)));s=io.StringIO();w=csv.writer(s);w.writerows([list(reversed(r)) for r in rs]);assert calculate(s.getvalue())['input_count']==49
def test_legacy_13_column_header_still_loads(raw):
    # 旧版无 monthly_sales 列的文件继续可读，销量字段降级为未提供。
    import csv,io
    rs=list(csv.reader(io.StringIO(raw)))
    legacy=[row[:-1] for row in rs]
    out=io.StringIO();csv.writer(out).writerows(legacy)
    result=calculate(out.getvalue())
    assert result['input_count']==49 and all(d.get('sales_n') is None for d in result['net_demands'])
