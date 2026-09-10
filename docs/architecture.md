# 架构和质量契约

一个仓库、一个 Python 包、单体模块化。domain 为冻结 DTO、Enum 及有限值/时间验证，无基础设施依赖。

acquisition → evidence → models → markets → decisions → reporting；application 编排，storage 只读写、校验文件与 hash，不包含足球判断。模型不依赖采集或 Word；报告不重新计算概率；禁止循环依赖。依赖 domain 的横向共享允许。没有数据库、工厂层或为未来功能预留接口。

公共函数必须标注类型；复杂数学为纯函数；状态用 Enum/Literal。禁止单行 if/class 和多语句函数体，禁止裸捕获 Exception 后继续。单文件超过约400行、函数超过约50行必须审查并记录理由。使用 JSON 文件作为任务快照，输出不进入源代码 Git 历史。

pytest 自动阻断 socket 网络，每个里程碑运行全部 pytest、diff --check、compileall、ruff。检查范围为新仓库，禁止为了“扫描旧代码”读取旧仓库；以初始新建提交、来源登记、依赖/禁用字符串扫描证明独立开发。
