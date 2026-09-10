# Codex 公开网页研究操作规范

此流程由 Codex 的网页搜索能力执行，Python 不连接网页，也不调用任何足球数据接口。用户自然语言任务启动后记录 UTC 起点并将明确截止时间转换为 UTC；“明早06:00”按 Asia/Shanghai 的次日解释。歧义时间需明确，不从系统 UTC 日期猜北京时间日期。

1. 搜索时间窗涉及的各日期赛程：按欧洲、亚洲、大洋洲、南美、北美、中美、非洲分别检索，另查女足、青年、杯赛和低级别。至少使用两个可访问独立赛程聚合页面；官方赛事页核验重点比赛。
2. 保存发现清单，不因无赔率删除。记录每个来源的日期、时区、访问失败或未覆盖范围。队名别名需有明确映射；同名不同梯队/女足/联赛不合并。开赛时间冲突先保留断言，未解决 PASS。
3. 打开公开赔率页面，摘录显示的完整市场、博彩公司、观察时间、规则、原始线与赔率格式。不可访问则换公开来源；不读取隐藏请求、不登录绕过。一次任务不等待再次刷新。
4. 保存允许保留的页面文本/HTML/CSV/JSON-LD，计算 SHA256；网页内容含敏感凭据不能保存。为每条来源建立 Evidence。每条模型历史统计、赛程事实、伤停、人员/战术断言附 evidence_id 和快照中可定位的原文引用。来源发布时间和盘口观察时间没有就留空。
5. 当前报价按博彩公司、完整市场、时段规则和同一观察时刻分组。多网站出现同一事实不同值时保留冲突，不能挑选更有利的值。初盘可得时单独保存为早期时点，报价移动不可伪造。热度、成交量无公开证据留空。
6. 重点比赛收集长期/近期同口径主客场历史、对手水平、联赛基准、xG/射门、伤停、休息/旅行/轮换、战术与动机。缺官方首发只说明，已知重大人员变动无可核验影响估计时阻止正式模型推荐。
7. 研究包 root 下保存 manifest.json 和 snapshots/。命令 `fq analyze --input manifest.json --output outputs/report.docx` 在后续主市场里程碑实现。所有输入都核验 hash 与 evidence_id。真实模式拒绝测试来源。输出 JSON 用于确定性审查，Word 必须渲染。

## 证据包字段

顶层：mode、started、deadline、generated、evidence、matches、coverage_notes。

evidence 各项遵循数据政策，另含 id、mode、snapshot_path。

matches 各项：fixture（id/home/away/competition/kickoff/evidence_ids）、quotes（market/selection/line/original_value/original_format/evidence_id/bookmaker/rules）、claims（key/value/evidence_id）、history（历史统计，后续模型规范）、notes、missing。每一断言需能在对应快照中定位。未提供的字段不构造数值默认值。

source_type、extraction_method 为审计文本标签，不能替代验证状态；validation_status 与 mode 用枚举。原始数据不进 Git；源码 fixture 仅可为明确合成的数据或合法且有真实来源的快照。记录采集失败，不以测试页代替真实覆盖。
