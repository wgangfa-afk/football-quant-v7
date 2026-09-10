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
