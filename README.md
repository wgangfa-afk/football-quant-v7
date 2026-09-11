# Football Quant V7

Codex 云端手动运行的单体模块化赛前足球分析项目。使用公开网页研究和可追溯快照，生成中文单场分析及 Word 报告。开发中，尚未完成真实报告验收。

## 正式规范

- [产品范围及验收](docs/product.md)
- [数据政策](docs/data-policy.md)
- [市场规范](docs/markets.md)
- [数学规范](docs/mathematics.md)
- [报告规范](docs/report.md)
- [架构规则](docs/architecture.md)

## 开发

Python 3.12+，`python -m pip install -e '.[dev]'`。

每个里程碑执行全量检查：

```sh
python -m pytest -q
git diff --check
python -m compileall -q src tests
python -m ruff check src tests
```

无需任何数据 API、密钥、投注账户或数据库。固定测试数据不能用于真实报告。

## 当前开发状态

M0—M4 已实现并分别提交；77项离线测试通过。**M5真实网页覆盖、真实报告和用户验收尚未完成**，因此不能宣称整个第一阶段已验收。

```sh
# 固定数学链路演示
PYTHONPATH=src python -m football_quant.application demo
# 包含主市场、角球、黄牌的合成研究包
PYTHONPATH=src python -m football_quant.application analyze --input fixtures/research-test/manifest.json --output outputs/test.docx
# 真实网页证据先由Codex按工作流采集，随后导入
PYTHONPATH=src python -m football_quant.application analyze --input task/manifest.json --output outputs/report.docx
```

见 [网页研究工作流](docs/research-workflow.md)、[研究包字段](docs/input-example.md)、[M4审查与限制](docs/m4-review.md)。Word渲染使用环境提供的 documents 技能及共享 Noto Sans CJK SC 字体，不在代码里安装或下载运行依赖。

真实模型未校准，目前方向最高C；罚牌仅支持一致的黄牌张数口径，其他积分规则PASS。负EV原样保留；不开发模拟账本。PR在M5完成后创建，未经用户确认不合并。
