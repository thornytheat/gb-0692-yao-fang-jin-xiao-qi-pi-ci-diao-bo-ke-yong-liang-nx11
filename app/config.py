import os
from pathlib import Path
RULE_VERSION = "2026.11.18.3"
TITLE = '药房近效期批次调拨与可用量'
SHORT = 'pharma-fefo'
MODULES = ['库存接收', '批号裁决', '效期分层', '需求净额', '调拨分配', '收发对账', '方案复核']
HEADERS = ['record', 'kind', 'sku', 'lot', 'qty', 'frozen', 'pack', 'expiry', 'store', 'min_days', 'arrival', 'version', 'status', 'monthly_sales']
SAMPLE = Path(__file__).resolve().parent.parent / "sample_data" / "operations.csv"
LIMIT = 10000
# 分配引擎：v2 为销量约束分配（默认）；legacy 为仅校验余期的旧规则。
# 单次运行可通过 JSON 入参 engine 覆盖；v2 运行异常时自动回退 legacy，旧批次与旧数据始终可用。
ENGINE_V2 = 'v2'
ENGINE_LEGACY = 'legacy'
def default_engine():
    return os.environ.get('APP_ENGINE', ENGINE_V2).strip().lower()
# 月均销量按 30 天折算日销量；到期前可售量 = 月均销量 * 可售天数 / 30。
MONTH_DAYS = 30
