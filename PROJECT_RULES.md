# 项目规则

## 1. 项目定位

本项目不是 demo，不是一次性脚本集合，也不是只为了跑通一个模型的临时实验。

本项目定位为正式、长期、可迭代、可发表论文或支撑高质量科研结论的研究代码项目。所有代码、实验、文档和结果都必须服务于以下目标：

- 可复现；
- 可扩展；
- 可解释；
- 可比较；
- 可审稿；
- 可长期维护；
- 可支撑论文发表或严肃科研交付。

## 2. 总体工程原则

### 2.1 不写一次性核心代码

禁止把核心流程写成只适用于当前文件路径、当前数据样本或当前实验的一次性脚本。

允许探索性 notebook 或临时脚本，但它们只能用于探索，不得作为最终 pipeline 的核心组成部分。稳定逻辑必须沉淀到模块化代码中。

### 2.2 模块之间低耦合、少依赖

模块设计必须遵循低耦合原则：

- 数据读取模块不依赖模型训练模块；
- 特征构建模块不依赖具体模型；
- 模型模块不依赖具体数据文件路径；
- 评价模块不依赖某个特定模型实现；
- 可解释性模块可以读取模型输出，但不应反向污染训练逻辑。

每个模块应该有清晰输入、清晰输出和清晰责任边界。

### 2.3 可替换、可扩展

后续可能新增模型、数据集、特征、评价方式和组学模态，因此所有设计都要方便替换：

- 可以替换数据集；
- 可以替换特征构建策略；
- 可以替换模型；
- 可以替换训练配置；
- 可以替换评价指标；
- 可以新增数据模态或实验任务。

如果某个设计会让后续替换变得困难，优先重新设计。

### 2.4 研究代码也要工程化

虽然这是科研项目，但代码质量必须接近正式工程项目，而不是随意堆叠实验代码。

基本要求：

- 函数职责单一；
- 类和模块命名清楚；
- 配置与代码分离；
- 数据路径不硬编码；
- 日志完整；
- 随机种子可控；
- 实验结果可追踪；
- 错误信息清楚；
- 关键流程有测试或校验。

## 3. 推荐代码组织

推荐结构：

```text
project/
├── configs/                 # 实验配置
├── data/                    # 本地数据入口，原则上不提交大文件
│   ├── raw/
│   ├── external/
│   ├── interim/
│   ├── processed/
│   └── metadata/
├── docs/                    # 文档、计划书、方法说明
├── notebooks/               # 探索性分析
├── results/                 # 结果输出，原则上不提交大文件
├── scripts/                 # 命令行入口脚本
├── src/                     # 核心源码
├── tests/                   # 单元测试与集成测试
├── project_plan.md          # 项目计划书
├── PROJECT_RULES.md         # 项目规则
└── README.md
```

如果采用其他结构，也必须保证职责边界清楚。

## 4. 数据规则

### 4.1 原始数据不可随意修改

原始数据必须保持只读。任何清洗、过滤、标准化和格式转换都应输出到新的中间文件或结果目录。

### 4.2 数据处理必须可追踪

每个 processed 数据都必须能够追踪来源：

- 来自哪个 raw 文件；
- 使用了哪个脚本；
- 使用了哪个配置；
- 生成时间；
- 过滤标准；
- 归一化方法；
- genome version、annotation version 或领域内等价版本信息。

### 4.3 严格避免数据泄漏

预测任务必须特别注意数据泄漏。根据任务类型，至少考虑：

- random split；
- sample / cell / patient holdout；
- feature / gene / target holdout；
- chromosome / region / group holdout；
- condition / time / batch holdout；
- tissue / cell line / cohort holdout。

论文主结果或核心结论不能只依赖最宽松的 random split。

## 5. 实验规则

### 5.1 所有实验必须配置化

实验参数不得散落在代码中。模型、数据、特征、训练参数和评价方式都应写入配置文件。

配置中至少包含：

- dataset；
- input features or modalities；
- feature version；
- split strategy；
- model name；
- model hyperparameters；
- random seed；
- training parameters；
- evaluation metrics；
- output directory。

### 5.2 实验必须可复现

每次实验至少记录：

- git commit；
- command；
- config file；
- package versions；
- random seed；
- input data version；
- output path；
- metrics；
- runtime；
- hardware information。

### 5.3 Benchmark 必须公平

不同模型比较时必须尽可能保持一致：

- 使用相同 train / validation / test split；
- 使用相同输入信息；
- 使用相同评价指标；
- 使用相同预处理版本；
- 明确区分模型能力和特征工程能力。

如果某个模型使用额外数据或预训练权重，必须在结果表中明确标注。

## 6. 模型开发规则

### 6.1 从强基线开始

任何复杂模型都必须和简单模型比较。根据领域选择合适基线，例如：

- mean / majority baseline；
- linear regression / logistic regression / ridge；
- random forest；
- XGBoost / LightGBM / CatBoost；
- shallow MLP；
- deep learning model；
- foundation model adapter。

如果复杂模型不能显著超过强基线，需要诚实报告，并分析原因。

### 6.2 模型接口统一

不同模型应尽量遵循统一接口：

```python
fit(train_data, valid_data, config)
predict(test_data)
evaluate(test_data)
save(path)
load(path)
```

模型内部可以不同，但外部训练、评价和保存方式应保持一致。

### 6.3 模型必须支持消融实验

涉及多特征、多模态或多组件贡献的核心模型，必须支持 ablation。不能做消融的模型，不适合作为核心结论唯一依据。

### 6.4 模型必须关注可解释性

本项目不是纯 prediction leaderboard。模型必须尽量回答“为什么”。

根据模型类型，至少支持一种解释方式：

- feature importance；
- SHAP；
- permutation importance；
- modality / feature family contribution；
- integrated gradients；
- attention attribution；
- graph explanation；
- in-silico deletion / perturbation。

## 7. 统计学与科学解释规则

### 7.1 不只报告整体平均值

所有核心结果都应根据领域做分层分析，例如：

- by sample / cell type / cohort / condition；
- by time point / phase / batch；
- by target class / gene class / feature class；
- by expression level or difficulty group；
- by biologically meaningful subgroup。

### 7.2 统计结论要有不确定性估计

重要结论不能只给一个点估计。应尽量报告：

- confidence interval；
- standard error；
- bootstrap result；
- multiple-testing correction；
- effect size；
- statistical significance；
- biological or domain significance。

### 7.3 科学解释优先于模型炫技

模型复杂度不是目标。每个关键模型结果都应尽量转化为领域表述：

- 哪些信息最重要；
- 哪类样本或目标最依赖这些信息；
- 哪些结果与已有知识一致；
- 哪些结果提出了新的可验证假设；
- 哪些负结果说明了真实上限。

## 8. 结果与论文规则

### 8.1 图表要服务主线

所有图表都应围绕项目主线，而不是堆叠漂亮但无关的结果。

### 8.2 结果必须可追溯

论文或报告中的每个数字、每张图、每个表格都应能追溯到：

- 原始数据；
- 处理脚本；
- 配置文件；
- 模型版本；
- 结果文件；
- 作图脚本。

### 8.3 负结果也要保留

如果某个模型没有提升，或某类信息贡献很小，也应记录。负结果对严肃科研项目很重要。

## 9. 文档规则

### 9.1 每个核心模块必须有说明

至少需要说明：

- 模块目的；
- 输入格式；
- 输出格式；
- 主要函数或类；
- 使用示例；
- 常见问题。

### 9.2 README 要面向新加入者

README 应帮助新加入项目的人快速理解：

- 项目目标；
- 数据来源；
- 环境安装；
- 如何运行最小 pipeline；
- 如何复现实验；
- 如何新增模型；
- 如何新增数据集或任务。

### 9.3 重要设计需要记录

关键技术选择应写入设计文档，而不是只存在聊天记录或个人记忆中。

### 9.4 Markdown 文档默认中文

后续新生成的说明类 Markdown 文档默认使用中文撰写，尤其是：

- README；
- 方法说明；
- runbook；
- 项目总结；
- prompt / result 记录；
- 设计文档；
- 排错说明；
- 实验报告。

代码标识、命令、配置键、字段名、文件路径、模型名称、指标名称、包名和标准英文技术术语可以保留英文，避免强行翻译降低准确性。

只有在用户明确要求英文、目标期刊/合作者需要英文、或必须保留英文原文对照时，才生成英文说明文档。

## 10. 代码质量规则

### 10.1 Python 代码规范

推荐遵循：

- Python 3.11+；
- type hints；
- dataclass / pydantic 用于结构化配置；
- pathlib 处理路径；
- logging 记录日志；
- pytest 编写测试；
- ruff / black 做格式化和静态检查。

### 10.2 函数和类设计

函数应该短而清楚。避免：

- 一个函数做完整 pipeline；
- 函数内部写死路径；
- 函数内部偷偷读取全局变量；
- 训练逻辑和画图逻辑混在一起；
- 数据清洗和模型训练混在一起。

### 10.3 错误处理

错误信息必须帮助定位问题。例如，不要只抛出：

```text
File not found
```

而应说明：

```text
Expected processed expression matrix at <path>. Please run `prepare_expression_matrix` first.
```

### 10.4 运行日志与进度反馈

任何可能运行超过几秒钟的脚本、命令或 pipeline，都必须提供清晰的日志或进度反馈，不能长时间静默运行。

基本要求：

- 命令行脚本应支持 `--log-level` 参数；
- Python 脚本应使用标准库 `logging`；
- 日志至少记录输入文件、输出文件、关键配置参数、数据规模、主要处理阶段、耗时阶段和完成状态；
- 长循环应按 sample、cell、chromosome、batch、chunk 或领域内自然单位给出阶段性进度；
- 日志不应泄露敏感信息，也不应刷屏。

## 11. 版本管理规则

### 11.1 不提交大数据文件

大型数据、模型权重和结果文件原则上不提交到 git。应通过 `.gitignore` 排除：

- raw data；
- processed large matrices；
- model checkpoints；
- tensorboard / wandb logs；
- temporary files；
- large figures；
- cache files。

### 11.2 提交要有清晰主题

每次 commit 应尽量围绕一个主题，例如：

- data pipeline；
- feature construction；
- baseline model；
- evaluation metrics；
- visualization；
- documentation。

### 11.3 不破坏已有结果

修改核心流程时，应确认：

- 旧配置是否还能运行；
- 旧结果是否还能解释；
- 是否需要 bump data / feature / model version；
- 是否需要更新文档。

## 12. 开发优先级

项目开发优先顺序：

1. 数据格式标准化；
2. 可复现 pipeline；
3. 统计学基线；
4. 传统机器学习强基线；
5. 严格 benchmark；
6. 可解释性分析；
7. 深度学习 / 图模型 / 高级模型；
8. 大模型迁移；
9. 科学案例分析；
10. 论文级图表和文档。

任何新想法都应放入这个优先级框架中评估，避免过早堆复杂模型。

## 13. 工作态度

本项目要按照正式科研项目推进：

- 不追求表面跑通；
- 不为了漂亮结果牺牲严谨性；
- 不用复杂模型掩盖数据问题；
- 不把 benchmark 写成不可复现的脚本；
- 不把临时结论当最终结论；
- 不忽视负结果；
- 不忽视统计学和领域解释。

最终交付物应该经得起以下检查：

- 换一个人能否复现；
- 换一个数据集能否扩展；
- 换一个模型能否接入；
- 审稿人能否相信；
- 领域专家能否理解；
- 后续论文或项目能否继续发展。

## 14. 对 AI/开发代理的要求

后续任何 AI 或开发者参与本项目时，必须遵循：

1. 先理解项目目标，再写代码。
2. 先阅读已有结构和规则，再新增模块。
3. 优先复用已有接口，不随意创造并行体系。
4. 新增功能必须考虑可复现、可测试和可扩展。
5. 不把核心逻辑写进 notebook。
6. 不写硬编码路径。
7. 不随意引入重依赖。
8. 不为了短期跑通破坏长期结构。
9. 修改公共接口时必须同步更新文档和调用方。
10. 每次完成工作都应说明改了什么、如何验证、还有什么风险。

### 14.1 AI 代理的低 token 上下文规则

为避免大型数据文件、日志和重复读取造成无意义的上下文消耗，AI 代理默认采用低 token 工作模式。节省 token 不能降低工程质量、验证强度或科研严谨性。

必须遵循：

1. 搜索优先于整文件读取。先用 `rg -n` 定位关键词、函数、配置项或标题，再读取必要的局部片段。
2. 大文件默认只读取有界片段。优先使用文件头、文件尾或指定行段，不直接展开完整长文档、manifest、TSV、JSON、日志或生成结果。
3. 大型结构化数据默认程序化摘要。优先统计行数、列数、唯一值数量、缺失率、重复键、文件大小和少量示例行，不把大量原始记录送入上下文。
4. 日志默认检查错误和尾部。优先搜索 `ERROR`、`WARNING`、`Traceback`，并读取有限的尾部内容；只有诊断需要时才扩大范围。
5. diff 默认逐级展开。先检查 `git status --short` 和 `git diff --stat`，再查看目标文件的局部 diff。
6. 不重复搬运已确认的信息。优先复用已有 summary、result、readiness、runbook 或 checkpoint 文档。
7. 对 IDE 自动附带的大型选区保持克制。除非当前任务确实依赖原始内容，否则把它视为背景引用，不复述、不整体分析、不再次载入。
8. 中间汇报只保留关键节点。说明当前阶段、重要发现、阻塞和验证结论。
9. 长任务必须将详细输出写入日志文件，终端和对话中只保留阶段进度、关键统计和最终摘要。
10. 当局部信息不足以保证正确性时，必须扩大读取范围，并简要说明扩大范围的原因。

低 token 模式不是跳过必要审计、测试或验证的理由。
