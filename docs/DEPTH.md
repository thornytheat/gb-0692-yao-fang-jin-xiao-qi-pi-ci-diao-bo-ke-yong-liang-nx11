# 深度登记 药房近效期批次调拨与可用量

- 规模：中型
- 使用者与工作流：连锁药房库存核对员，汇集批号库存与调拨申请，按可用有效期安排门店补货。
- 核心规则：FEFO仅分配到店后剩余有效期满足需求的库存；冻结量先扣，拆包需整包装，召回批不得调拨。

## 功能模块

| 模块 | 使用者动作 | 入口 | 核心文件 | 测试 |
|---|---|---|---|---|
| M1 库存接收 | 运行库存接收并复核证据 | `POST /api/m1`；`/work/1` | `app/modules/m1_receiving/rules.py` | `tests/test_m1.py` |
| M2 批号裁决 | 运行批号裁决并复核证据 | `POST /api/m2`；`/work/2` | `app/modules/m2_lots/rules.py` | `tests/test_m2.py` |
| M3 效期分层 | 运行效期分层并复核证据 | `POST /api/m3`；`/work/3` | `app/modules/m3_expiry/rules.py` | `tests/test_m3.py` |
| M4 需求净额 | 运行需求净额并复核证据 | `POST /api/m4`；`/work/4` | `app/modules/m4_demand/rules.py` | `tests/test_m4.py` |
| M5 调拨分配 | 运行调拨分配并复核证据 | `POST /api/m5`；`/work/5` | `app/modules/m5_allocation/rules.py` | `tests/test_m5.py` |
| M6 收发对账 | 运行收发对账并复核证据 | `POST /api/m6`；`/work/6` | `app/modules/m6_reconcile/rules.py` | `tests/test_m6.py` |
| M7 方案复核 | 运行方案复核并复核证据 | `POST /api/m7`；`/work/7` | `app/modules/m7_approval/rules.py` | `tests/test_m7.py` |

## 陷阱登记

| TRAP | 现象 | 朴素实现会怎样 | 本项目处理 | 处理位置 | 测试 |
|---|---|---|---|---|---|
| TRAP-02 | BOM | 静默覆盖或误计 | 显式裁决并保留证据 | `app/modules/m1_receiving/rules.py` | `tests/test_m1.py::test_bom` |
| TRAP-05 | 列数不齐 | 静默覆盖或误计 | 显式裁决并保留证据 | `app/modules/m1_receiving/rules.py` | `tests/test_m1.py::test_bad_columns` |
| TRAP-07 | 空值数量 | 静默覆盖或误计 | 显式裁决并保留证据 | `app/modules/m2_lots/rules.py` | `tests/test_m2.py::test_missing_quantity` |
| TRAP-08 | 药品编码前导零 | 静默覆盖或误计 | 显式裁决并保留证据 | `app/modules/m2_lots/rules.py` | `tests/test_m2.py::test_sku_leading_zero` |
| TRAP-14 | 同单冲突 | 静默覆盖或误计 | 显式裁决并保留证据 | `app/modules/m2_lots/rules.py` | `tests/test_m2.py::test_conflict_not_override` |
| TRAP-19 | 召回优先 | 静默覆盖或误计 | 显式裁决并保留证据 | `app/modules/m2_lots/rules.py` | `tests/test_m2.py::test_recall_dominates` |
| TRAP-23 | 效期端点 | 静默覆盖或误计 | 显式裁决并保留证据 | `app/modules/m3_expiry/rules.py` | `tests/test_m3.py::test_expired_isolated` |
| TRAP-26 | 陈旧复核 | 静默覆盖或误计 | 显式裁决并保留证据 | `app/modules/m7_approval/rules.py` | `tests/test_m7.py::test_review_api_stale` |
| TRAP-31 | 近效期压慢店致报损 | 只看余期满配，到期卖不完 | 按到期前可售量设上限，卖不完留仓并逐批报告 | `app/domain.py::allocate_v2` | `tests/test_m5_v2.py::test_slow_store_capped_and_near_expiry_left_in_warehouse` |
| TRAP-32 | 新引擎上线失败 | 旧逻辑被替换，故障即停摆 | 旧引擎保留可选，异常自动回退并隔离留证 | `app/modules/m5_allocation/rules.py` | `tests/test_m5_v2.py::test_engine_failure_falls_back_with_quarantine` |
| TRAP-33 | 重跑重复下发/覆盖台账 | 同批再跑生成重复调拨，历史被覆盖不可恢复 | 台账只追加，幂等键去重，无更新删除接口 | `app/store.py::dispatch` | `tests/test_dispatch.py::test_dispatch_idempotent_no_duplicates` |

## 对账规则

输入记录 = 采信记录 + 隔离记录 + 相同行重复。重复表头与空行单独记数。业务合计按阶段中的守恒或差值列复核。运行清单有原文SHA256、规则版本与耗时；相同规则版本下同文重复提交复用批次。

## 已知不覆盖

部署为本地单用户工具，不连接外部上游系统。CSV单文件5MB及一万条业务记录上限；不推断未提供的未知数据。
