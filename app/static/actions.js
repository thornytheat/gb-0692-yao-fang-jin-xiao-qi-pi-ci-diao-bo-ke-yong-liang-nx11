const pharmacy={pending:false,plan:JSON.parse(document.getElementById('plan').textContent)};const message=document.getElementById('message');
async function savePlan(endpoint,body){if(pharmacy.pending)return;pharmacy.pending=true;message.textContent='正在安排批号…';for(const b of document.querySelectorAll('button'))b.disabled=true;try{let request={method:'POST',body:body};if(!(body instanceof FormData)){request.body=JSON.stringify(body);request.headers={'Content-Type':'application/json'}}let response=await fetch(endpoint,request),result=await response.json();if(response.status>=400)throw Error(result.message);if(result.manifest){location.href=location.pathname+'?run_id='+encodeURIComponent(result.manifest.run_id)}else{location.reload()}}catch(e){message.textContent=e.message||'提交失败，请重试'}finally{pharmacy.pending=false;for(const b of document.querySelectorAll('button'))b.disabled=false}}
document.getElementById('demo').addEventListener('click',()=>savePlan('/api/run',{}));document.getElementById('commit').addEventListener('click',()=>savePlan('/api/run',{csv:document.getElementById('source').value}));document.getElementById('sendfile').addEventListener('click',()=>{let f=document.getElementById('attachment').files[0];if(!f){message.textContent='先选择库存文件。';return}let data=new FormData();data.append('file',f);savePlan('/api/run',data)});document.querySelectorAll('[data-approve]').forEach(el=>el.addEventListener('click',()=>savePlan('/api/review',{...pharmacy.plan,decision:el.dataset.approve})));document.getElementById('paper').addEventListener('click',()=>window.print());
const ledgerBody=document.getElementById('ledger-body');
if(ledgerBody){(async()=>{
  try{
    let resp=await fetch('/api/transfers?run_id='+encodeURIComponent(pharmacy.plan.id));
    let rows=await resp.json();
    document.getElementById('ledger-count').textContent=rows.length+' 条';
    if(!rows.length)return;
    ledgerBody.innerHTML=rows.map(r=>`<tr><td>${r.record}</td><td>${r.store}</td><td>${r.sku}</td><td>${r.lot}</td><td>${r.qty}</td><td>${r.engine}</td><td>${r.created_at}</td></tr>`).join('');
  }catch(e){document.getElementById('ledger-count').textContent='台账读取失败';}
})();}
const dispatchBtn=document.getElementById('dispatch');
if(dispatchBtn){dispatchBtn.addEventListener('click',async()=>{
  if(pharmacy.pending)return;
  if(pharmacy.plan.decision!=='通过'){message.textContent='方案尚未复核通过，不能下发。';return;}
  pharmacy.pending=true;dispatchBtn.disabled=true;message.textContent='正在下发调拨单（台账只追加，不覆盖历史）…';
  try{
    let resp=await fetch('/api/dispatch',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id:pharmacy.plan.id})});
    let result=await resp.json();
    if(resp.status>=400)throw Error(result.message);
    message.textContent='下发完成：新增 '+result.inserted+' 条，跳过重复 '+result.duplicate_skipped+' 条，台账共 '+result.total+' 条（引擎 '+result.engine+'）。';
    dispatchBtn.textContent='已下发（重跑不重复）';
  }catch(e){message.textContent=e.message||'下发失败，请重试';dispatchBtn.disabled=false;}finally{pharmacy.pending=false;}
});}
