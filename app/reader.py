import csv, io
from app.config import HEADERS, LIMIT
from app.errors import DomainError
from app.reasons import isolate
OPTIONAL = {'monthly_sales'}
def decode(raw):
    for encoding in ('utf-8-sig','gb18030'):
        try: return raw.decode(encoding)
        except UnicodeDecodeError: pass
    raise DomainError('ENCODING','无法识别文件编码')
def read_rows(ctx):
    text=ctx['text'].lstrip('﻿')
    if not text: raise DomainError('EMPTY','输入为空')
    reader=csv.reader(io.StringIO(text, newline=''), strict=True)
    try: head=next(reader,None)
    except csv.Error: raise DomainError('STRUCTURE','表头损坏')
    if head is None: raise DomainError('BLANK','文件仅有空行')
    head=[x.strip() for x in head]
    # 必填列必须齐全且不重复；可选列（如月均销量）允许整列缺省，旧版 13 列文件继续可读。
    required=[h for h in HEADERS if h not in OPTIONAL]
    if set(head) not in (set(HEADERS), set(required)) or len(head)!=len(set(head)):
        raise DomainError('HEADER','字段缺失或重复')
    width=len(head)
    rows=[];ctx['input_count']=0;ctx['blank_count']=0;ctx['header_count']=0
    try:
        for cells in reader:
            if len(rows)+len(ctx['quarantine']) >= LIMIT: raise DomainError('LIMIT','文件超过一万行')
            if not cells or all(not x.strip() for x in cells): ctx['blank_count']+=1;continue
            if cells==head: ctx['header_count']+=1;continue
            ctx['input_count']+=1
            if len(cells)!=width:
                # 兼容旧版 13 列行（仅缺尾部可选列）；其余列数不符一律隔离。
                if width==len(HEADERS) and len(cells)==len(required):
                    cells=cells+['']
                else:
                    isolate(ctx,{'行号':reader.line_num,'原值':'|'.join(cells)},'COLUMNS','列数不符');continue
            row=dict(zip(head,[x.strip() for x in cells]))
            for missing in OPTIONAL: row.setdefault(missing,'')
            rows.append({**row,'行号':reader.line_num})
    except csv.Error: raise DomainError('STRUCTURE','引号未闭合或记录截断')
    if not rows and not ctx['quarantine']: raise DomainError('HEADER_ONLY' if not ctx['blank_count'] else 'BLANK','文件没有业务记录')
    ctx['rows']=rows
    return rows
