# 真实研究包导入说明

运行 `PYTHONPATH=src python -m football_quant.application analyze --input task/manifest.json --output outputs/report.docx`。同时输出同名JSON；此命令不执行网络访问，Codex 先按 research-workflow.md 收集公开网页。

每条报价除文档中字段外带 excerpt，必须是其 evidence_id 对应快照中的原文片段。每条 claim 同样带 excerpt。history 包含 baseline 和 home/away 两组历史：

- baseline: home、away（联赛主客进球均值）、same_basis（布尔，跨联赛无桥接为false）、evidence_id、excerpt。
- 历史行: played（aware）、venue（home/away）、goals_for、goals_against、opponent_attack、opponent_defence、xg_for/xg_against（可空）、xg_provider（有xG必填）、evidence_id、excerpt。
- claim key 建议 personnel/tactics/schedule/motivation；确认重大变化使用 major_change，value!=none 将阻止未经调整的模型推荐。其他冲突同样保留。

manifest 必须自己提供本次任务的 started、deadline、generated。重跑固定输入应使用固定 generated 复现历史判断；提供给用户的当前报告应使用实际生成时刻重新检查比赛是否已开赛。实际研究不能把测试时间或合成快照换名后使用。

辅助统计：history.corners / history.cards，分别包含 units 与 home_for/home_against/away_for/away_against；每项是至少8条 {count, units, evidence_id, excerpt}。角球 units=corners，罚牌 units=yellow_cards。报价 rules 分别为 regular_time_corners / regular_time_yellow_cards；其他牌分规则当前明确PASS。历史数据必须由研究者核实为对应主客场拆分，不将同场重复记录作独立样本。

真实 analyze 默认采用实际 UTC 生成时刻，防止旧manifest把已开赛比赛重新列为方向。历史复现可显式指定 `--generated-at 2030-01-01T10:00:00+00:00`。模型计算仍为固定输入的确定性纯函数。

同一博彩公司、市场、方向、盘口线及规则的早期观察只能作为历史报价；只有最新可见观察参与当前推荐。不同观察时刻不算冲突，同一时刻原值不同则保留冲突。无法取得的初盘/热度/成交量必须记入missing，不能声称已分析其变化。
