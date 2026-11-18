import hashlib, time
from app.config import RULE_VERSION
def make(text, engine=None):
    digest=hashlib.sha256(text.encode('utf-8')).hexdigest()
    identity=RULE_VERSION+':'+digest+((':'+str(engine)) if engine else '')
    return {'run_id':hashlib.sha256(identity.encode('utf-8')).hexdigest()[:16], 'sha256':digest, 'rule_version':RULE_VERSION, 'parameters':{'engine':engine} if engine else {}, 'created_at':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())}
