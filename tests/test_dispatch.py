def test_dispatch_requires_approval(client):
    run=client.post('/api/run',json={}).get_json()
    resp=client.post('/api/dispatch',json={'id':run['manifest']['run_id']})
    assert resp.status_code==409 and resp.get_json()['code']=='REVIEW'

def test_dispatch_idempotent_no_duplicates(client):
    run=client.post('/api/run',json={}).get_json();ident=run['manifest']['run_id']
    client.post('/api/review',json={'id':ident,'revision':1,'decision':'通过'})
    first=client.post('/api/dispatch',json={'id':ident}).get_json()
    second=client.post('/api/dispatch',json={'id':ident}).get_json()
    rows=client.get('/api/transfers?run_id='+ident).get_json()
    assert first['inserted']==len(run['stages']['5']['rows'])
    assert second['inserted']==0 and second['duplicate_skipped']==len(rows)
    assert first['total']==second['total']==len(rows)
    # 同批数据重跑后再下发，台账仍不重复
    client.post('/api/run',json={})
    third=client.post('/api/dispatch',json={'id':ident}).get_json()
    assert third['total']==len(rows) and len(client.get('/api/transfers').get_json())==len(rows)

def test_dispatched_records_survive_new_runs(client, raw):
    run=client.post('/api/run',json={}).get_json();ident=run['manifest']['run_id']
    client.post('/api/review',json={'id':ident,'revision':1,'decision':'通过'})
    client.post('/api/dispatch',json={'id':ident})
    before=client.get('/api/transfers?run_id='+ident).get_json()
    # 提交不同数据产生新批次，不覆盖旧批次台账
    other=client.post('/api/run',json={'csv':raw+'\n'}).get_json()
    client.post('/api/review',json={'id':other['manifest']['run_id'],'revision':1,'decision':'通过'})
    client.post('/api/dispatch',json={'id':other['manifest']['run_id']})
    after=client.get('/api/transfers?run_id='+ident).get_json()
    assert before==after and len(client.get('/api/transfers').get_json())>len(before)

def test_dispatch_unknown_run_404(client):
    assert client.post('/api/dispatch',json={'id':'nope'}).status_code==404

def test_dispatch_requires_id(client):
    assert client.post('/api/dispatch',json={}).status_code==400

def test_legacy_batch_dispatch_uses_legacy_engine(client):
    run=client.post('/api/run',json={'engine':'legacy'}).get_json();ident=run['manifest']['run_id']
    client.post('/api/review',json={'id':ident,'revision':1,'decision':'通过'})
    out=client.post('/api/dispatch',json={'id':ident}).get_json()
    assert out['engine']=='legacy'
    assert all(t['engine']=='legacy' for t in client.get('/api/transfers?run_id='+ident).get_json())
