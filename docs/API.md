# 接口

`POST /api/run`：JSON中的csv文本，省略使用样例；或multipart字段file。最大5MB。

`POST /api/m1`至`POST /api/m7`：独立运行到指定模块，JSON结构同运行接口。

`GET /api/history`：历史批次。`POST /api/review`接收id、revision和decision（通过或退回）。`GET /api/evidence.csv`提供单一证据导出。

结构错误422，版本变化409，文件过大413；错误返回code与message。所有页面可从左侧七个模块入口访问。

`GET /api/runs/<id>`读取指定批次；页面与证据CSV通过run_id查询参数绑定批次，模块导航保留该参数。

JSON请求体必须是对象，数组、标量、null、损坏JSON及错误上传字段返回400，且不运行默认样例。

`POST /api/run`与`POST /api/m5`可在JSON中带`engine`（`v2`或`legacy`）选择分配引擎，缺省取环境变量`APP_ENGINE`，再缺省为`v2`。引擎作为批次身份的一部分，同文不同引擎生成不同run_id。v2运行异常自动回退legacy并写入`ENGINE`隔离记录，旧批次与13列旧文件始终可读。

`POST /api/dispatch`接收`{id}`下发调拨单：仅当批次复核状态为「通过」时允许，否则409。台账`transfers`只追加，主键`(run_id,record,lot)`配合`INSERT OR IGNORE`保证同一批数据重跑不产生重复调拨记录，且不提供更新/删除接口，已下发记录不可覆盖、可随时经`GET /api/transfers?run_id=<id>`恢复查询。返回`inserted`（本次新增）、`duplicate_skipped`（重跑跳过）、`total`（台账总数）。
