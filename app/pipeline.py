from app.modules.m1_receiving.service import execute as stage1
from app.modules.m2_lots.service import execute as stage2
from app.modules.m3_expiry.service import execute as stage3
from app.modules.m4_demand.service import execute as stage4
from app.modules.m5_allocation.service import execute as stage5
from app.modules.m6_reconcile.service import execute as stage6
from app.modules.m7_approval.service import execute as stage7
from app.config import SAMPLE, ENGINE_V2, ENGINE_LEGACY, default_engine
from app.manifest import make
from app.numeric import serial
from time import perf_counter
def calculate(text=None, stop=7, engine=None):
    started=perf_counter()
    if text is None: text=SAMPLE.read_text(encoding='utf-8-sig')
    if not isinstance(text,str):
        from app.errors import DomainError
        raise DomainError('TYPE','CSV必须是文本')
    engine=(engine or default_engine()).strip().lower()
    if engine not in (ENGINE_V2, ENGINE_LEGACY): engine=default_engine()
    ctx={'text':text,'rows':[],'quarantine':[],'stages':{},'manifest':make(text,engine),'engine':engine}
    for stage in STAGES[:stop]: stage(ctx)
    ctx['manifest']['elapsed_ms']=round((perf_counter()-started)*1000,3)
    ctx['manifest']['parameters']={'engine':ctx.get('engine',engine)}
    ctx.pop('text',None)
    return serial(ctx)
STAGES=[stage1,stage2,stage3,stage4,stage5,stage6,stage7]
