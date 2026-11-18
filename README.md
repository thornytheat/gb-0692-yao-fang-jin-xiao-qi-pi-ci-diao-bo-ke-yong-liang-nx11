# 药房近效期批次调拨与可用量

连锁药房库存核对员使用本工具完成：汇集批号库存与调拨申请，按可用有效期安排门店补货。

## 业务

FEFO仅分配到店后剩余有效期满足需求的库存；冻结量先扣，拆包需整包装，召回批不得调拨。七个模块：库存接收、批号裁决、效期分层、需求净额、调拨分配、收发对账、方案复核。模块独立API及页面入口见docs/API.md。样例中包含真实常见脏数据，原因码和原始行号在隔离面板及证据文件中可复核。

M5调拨分配提供两套引擎：默认`v2`在余期达标前提下，按门店近三个月月均销量（`monthly_sales`可选列）计算每批药「到期前可售量」，慢店只发到期前能卖完的量、卖不完的近效期留在中心仓，同药品近效期优先给周转快的门店；页面逐单显示预计能否售完与仍缺数量，并逐批列出仓内近效期余量。月均销量缺失或无效时该单自动降级为旧规则（只校验余期）。可用请求参数`engine=legacy`或环境变量`APP_ENGINE=legacy`切回旧引擎；v2运行异常也会自动回退旧引擎并在隔离清单留证。复核通过后经`POST /api/dispatch`下发，调拨台账只追加、同批重跑不重复、已下发记录不覆盖可恢复。

## 启动与验证

```sh
docker compose up --build -d
docker compose exec -T app pytest -q
docker compose config --quiet
```

打开 http://localhost:18206 。点击“运行样例”，或展开输入区提交CSV。切换七个模块查看计算依据。复核区可通过或退回，同一版本仅允许一次复核。证据CSV包含所有阶段与隔离行，批次内容不因复核变更。

SQLite保存在命名卷records；容器重建保留历史。只在确认不再需要数据时执行 `docker compose down -v` 重建。端口可通过.env中的PORT调整。本地也可 `pip install -r requirements.txt` 后 `python -m app.main`。

## 定义与限制

详见docs/DATA-DICTIONARY.md、docs/DEPTH.md。单文件最大5MB/一万行，本工具按确定性文件离线复算，不查询外部业务系统。源码位于app，测试位于tests，样例位于sample_data。
