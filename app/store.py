import sqlite3, json, os
from pathlib import Path
from app.errors import DomainError
def connection():
    path=Path(os.environ.get('APP_DB','data/runs.sqlite3'));path.parent.mkdir(parents=True,exist_ok=True)
    db=sqlite3.connect(path);db.row_factory=sqlite3.Row
    db.execute('CREATE TABLE IF NOT EXISTS runs(id TEXT PRIMARY KEY, payload TEXT NOT NULL, revision INTEGER NOT NULL DEFAULT 1, decision TEXT NOT NULL DEFAULT "待复核")')
    # 调拨下发台账：只追加。唯一键保证同批同单重跑不重复；不提供更新/删除接口，历史永远可恢复。
    db.execute('''CREATE TABLE IF NOT EXISTS transfers(
        run_id TEXT NOT NULL, record TEXT NOT NULL, store TEXT NOT NULL, sku TEXT NOT NULL,
        lot TEXT NOT NULL, qty INTEGER NOT NULL, engine TEXT NOT NULL,
        created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now')),
        PRIMARY KEY(run_id, record, lot))''')
    return db
def save(result):
    with connection() as db:
        ident=result['manifest']['run_id'];row=db.execute('SELECT payload,revision,decision FROM runs WHERE id=?',(ident,)).fetchone()
        if row: return {**json.loads(row['payload']), 'revision':row['revision'], 'decision':row['decision'], 'reused':True}
        db.execute('INSERT INTO runs(id,payload) VALUES (?,?)',(ident,json.dumps(result,ensure_ascii=False)))
    return {**result,'revision':1,'decision':'待复核','reused':False}
def get_run(ident):
    with connection() as db: row=db.execute('SELECT payload,revision,decision FROM runs WHERE id=?',(ident,)).fetchone()
    if row is None: raise DomainError('NOT_FOUND','批次不存在',404)
    return {**json.loads(row['payload']),'revision':row['revision'],'decision':row['decision']}
def latest():
    with connection() as db: row=db.execute('SELECT payload,revision,decision FROM runs ORDER BY rowid DESC LIMIT 1').fetchone()
    return {**json.loads(row['payload']),'revision':row['revision'],'decision':row['decision']} if row else None
def history():
    with connection() as db: return [dict(r) for r in db.execute('SELECT id,revision,decision FROM runs ORDER BY rowid DESC')]
def review(ident, revision, decision):
    if decision not in ('通过','退回'): raise DomainError('DECISION','复核动作无效')
    with connection() as db:
        changed=db.execute('UPDATE runs SET revision=revision+1,decision=? WHERE id=? AND revision=?',(decision,ident,revision)).rowcount
        if not changed: raise DomainError('VERSION','版本已变化，请重新载入',409)
    return {'revision':revision+1,'decision':decision}
def dispatch(ident):
    # 幂等下发：同一批数据重跑只插入缺失行，已写入的调拨记录不覆盖、不删除。
    run=get_run(ident)
    if run.get('decision')!='通过':
        raise DomainError('REVIEW','方案尚未复核通过，不能下发',409)
    engine=run.get('engine') or run['stages']['5'].get('engine','legacy')
    rows=run['stages']['5']['rows']
    inserted=0
    with connection() as db:
        for r in rows:
            cur=db.execute('''INSERT OR IGNORE INTO transfers(run_id,record,store,sku,lot,qty,engine)
                              VALUES(?,?,?,?,?,?,?)''',
                           (ident,r['需求单'],r['门店'],r['药品'],r['批号'],int(r['调拨数量']),engine))
            inserted+=cur.rowcount
        total=db.execute('SELECT COUNT(*) AS n FROM transfers WHERE run_id=?',(ident,)).fetchone()['n']
    return {'run_id':ident,'inserted':inserted,'total':total,'duplicate_skipped':len(rows)-inserted,
            'engine':engine,'decision':run['decision']}
def transfers(ident=None):
    with connection() as db:
        if ident:
            sql='SELECT run_id,record,store,sku,lot,qty,engine,created_at FROM transfers WHERE run_id=? ORDER BY rowid'
            return [dict(r) for r in db.execute(sql,(ident,))]
        return [dict(r) for r in db.execute('SELECT run_id,record,store,sku,lot,qty,engine,created_at FROM transfers ORDER BY rowid')]
