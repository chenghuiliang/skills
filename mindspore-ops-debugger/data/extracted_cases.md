# 新增案例研究（来自 GitCode org-issues）

基于最新 GitCode issue 文件提取的结构化根因分析案例。


## 精度/数值


### Case CS-021: 兼容性deepseek3网络，断点续训精度对不齐-org-issues-AtomGit | GitCode (#42119)


| 字段 | 内容 |
|------|------|
| 问题 | pangu_sigma2.3编译耗时优化未达预期 |
| 根因 | > 1、 2.3上某些pass相比于2.2版本的实现，存在性能劣化 > 2、 2.3版本把trace功能下掉了，导致前端编译劣化 > |
| 修复 | > 1、修复性能劣化的前端图优化pass > 2、通过支持boost infer功能把trace功能下掉导致的性能劣化拿回来 > |
| 引入类型 | 特性合入引入 / Bugfix修复引入 / 测试新增测试场景 / 测试漏测 / 用例未适配 / 环境问题 / CANN升级 |
| 状态 |  |

**关键教训**: > 1、 2.3上某些pass相比于2.2版本的实现，存在性能劣化 > 2、 2.3版本把trace功能下掉了，导致前端编译劣化 >


### Case CS-022: mint.nn.Linear fp32 910b偶现精度问题-org-issues-AtomGit | GitCode (#41931)


| 字段 | 内容 |
|------|------|
| 问题 | pangu_sigma2.3编译耗时优化未达预期 |
| 根因 | > 1、 2.3上某些pass相比于2.2版本的实现，存在性能劣化 > 2、 2.3版本把trace功能下掉了，导致前端编译劣化 > |
| 修复 | > 1、修复性能劣化的前端图优化pass > 2、通过支持boost infer功能把trace功能下掉导致的性能劣化拿回来 > |
| 引入类型 | 特性合入引入 / Bugfix修复引入 / 测试新增测试场景 / 测试漏测 / 用例未适配 / 环境问题 / CANN升级 |
| 后端 | - |
| 状态 | DONE |

**关键教训**: > 1、 2.3上某些pass相比于2.2版本的实现，存在性能劣化 > 2、 2.3版本把trace功能下掉了，导致前端编译劣化 >


### Case CS-023: [Bug]mindone transformers下的modeling clip训练精度概率性不达标-org-issues-AtomGit | GitCode (#41970)


| 字段 | 内容 |
|------|------|
| 问题 | pangu_sigma2.3编译耗时优化未达预期 |
| 根因 | > 1、 2.3上某些pass相比于2.2版本的实现，存在性能劣化 > 2、 2.3版本把trace功能下掉了，导致前端编译劣化 > |
| 修复 | > 1、修复性能劣化的前端图优化pass > 2、通过支持boost infer功能把trace功能下掉导致的性能劣化拿回来 > |
| 引入类型 | 特性合入引入 / Bugfix修复引入 / 测试新增测试场景 / 测试漏测 / 用例未适配 / 环境问题 / CANN升级 |
| 后端 | - |
| 状态 | DONE |

**关键教训**: > 1、 2.3上某些pass相比于2.2版本的实现，存在性能劣化 > 2、 2.3版本把trace功能下掉了，导致前端编译劣化 >


### Case CS-024: 【自提单】【MindFormers】训练前向推理开启pp并行时报错-org-issues-AtomGit | GitCode (#41944)


| 字段 | 内容 |
|------|------|
| 问题 | 训练前向pp并行下报错 |
| 根因 | 1. trainer中拦截; 取消拦截后存在精度问题，需要配置对应context |
| 修复 | [https://gitee.com/mindspore/mindformers/pulls/7965](https://gitee.com/mindspore/mindformers/pulls/7965)  [https://gitee.com/mindspore/mindformers/pulls/7909](https://gitee.com/mindspore/mindformers/pulls/7909); 在训练前向模式下取消拦截; 在pp > 1时，增加boardcast_pipeline_result=True的context  # |
| 后端 | - |
| 状态 | DONE |

**关键教训**: 1. trainer中拦截; 取消拦截后存在精度问题，需要配置对应context


### Case CS-025: nn.Conv2d fp16偶现精度问题-org-issues-AtomGit | GitCode (#41974)


| 字段 | 内容 |
|------|------|
| 问题 | pangu_sigma2.3编译耗时优化未达预期 |
| 根因 | > 1、 2.3上某些pass相比于2.2版本的实现，存在性能劣化 > 2、 2.3版本把trace功能下掉了，导致前端编译劣化 > |
| 修复 | > 1、修复性能劣化的前端图优化pass > 2、通过支持boost infer功能把trace功能下掉导致的性能劣化拿回来 > |
| 引入类型 | 特性合入引入 / Bugfix修复引入 / 测试新增测试场景 / 测试漏测 / 用例未适配 / 环境问题 / CANN升级 |
| 后端 | - |
| 状态 | DONE |

**关键教训**: > 1、 2.3上某些pass相比于2.2版本的实现，存在性能劣化 > 2、 2.3版本把trace功能下掉了，导致前端编译劣化 >


### Case CS-026: [Bug]python3.12，mindone diffusers下的generic modules部分模型训练精度不达标-org-issues-AtomGit | GitCode (#41925)


| 字段 | 内容 |
|------|------|
| 问题 | pangu_sigma2.3编译耗时优化未达预期 |
| 根因 | > 1、 2.3上某些pass相比于2.2版本的实现，存在性能劣化 > 2、 2.3版本把trace功能下掉了，导致前端编译劣化 > |
| 修复 | > 1、修复性能劣化的前端图优化pass > 2、通过支持boost infer功能把trace功能下掉导致的性能劣化拿回来 > |
| 引入类型 | 特性合入引入 / Bugfix修复引入 / 测试新增测试场景 / 测试漏测 / 用例未适配 / 环境问题 / CANN升级 |
| 后端 | - |
| 状态 | DONE |

**关键教训**: > 1、 2.3上某些pass相比于2.2版本的实现，存在性能劣化 > 2、 2.3版本把trace功能下掉了，导致前端编译劣化 >


### Case CS-027: 【自提单】【MindFormers】【pynative】TransformerLayer与TransformerBlock接口缺少精度用例-org-issues-AtomGit | GitCode (#42117)


| 字段 | 内容 |
|------|------|
| 问题 | pangu_sigma2.3编译耗时优化未达预期 |
| 根因 | > 1、 2.3上某些pass相比于2.2版本的实现，存在性能劣化 > 2、 2.3版本把trace功能下掉了，导致前端编译劣化 > |
| 修复 | > 1、修复性能劣化的前端图优化pass > 2、通过支持boost infer功能把trace功能下掉导致的性能劣化拿回来 > |
| 引入类型 | 特性合入引入 / Bugfix修复引入 / 测试新增测试场景 / 测试漏测 / 用例未适配 / 环境问题 / CANN升级 |
| 后端 | Ascend |
| 状态 | DONE |

**关键教训**: > 1、 2.3上某些pass相比于2.2版本的实现，存在性能劣化 > 2、 2.3版本把trace功能下掉了，导致前端编译劣化 >


### Case CS-028: ops.renorm ascend后端正向存在精度问题-org-issues-AtomGit | GitCode (#41975)


| 字段 | 内容 |
|------|------|
| 问题 | ops.renorm ascend后端正向存在精度问题 |
| 根因 | renorm算子实现有改动 |
| 修复 | 1、CANN同事已修正renorm实现，更新CANN包至最新版本，精度正确。 |
| 引入类型 | CANN升级 |
| 后端 | - |
| 状态 | DONE |

**关键教训**: renorm算子实现有改动


### Case CS-029: [Bug]mindone diffusers下的I2VGenXLUNet模型训练精度不达标-org-issues-AtomGit | GitCode (#42126)


| 字段 | 内容 |
|------|------|
| 问题 | I2VGenXLUNet模型精度未达标 |
| 根因 | mindone版本过老，模型未切换为mint算子，精度不足 |
| 修复 | 修改测试仓中mindone代码，将精度未达标模型切换为mint算子 |
| 引入类型 | 代码未适配 |
| 后端 | - |
| 状态 | DONE |

**关键教训**: mindone版本过老，模型未切换为mint算子，精度不足


### Case CS-030: ops.exp2 fp16偶现精度问题-org-issues-AtomGit | GitCode (#42160)


| 字段 | 内容 |
|------|------|
| 问题 | exp2 在float16的一维反向用例中有精度问题 |
| 根因 | 1、测试仓对比精度的函数没有适配算子精度比较的规则，对于float16的算子，标杆要先转成float32，然后计算完后转成float16比较，参看文档https://wiki.huawei.com/domains/21427/wiki/40193/WIKI202509168307538 |
| 修复 | 1、对齐算子比较标准，撤回提交https://codehub-y.huawei.com/MindSpore-enterprise/MindSpore-test/MindSporeTest/files/commit/1f0a09495c26cf26e970fff7a1d0e6affeca384c?ref=master |
| 引入类型 | 用例未适配 |
| 后端 | Ascend |
| 状态 | DONE |

**关键教训**: 1、测试仓对比精度的函数没有适配算子精度比较的规则，对于float16的算子，标杆要先转成float32，然后计算完后转成float16比较，参看文档https://wiki.huawei.com/d...


### Case CS-031: CPU后端trace算子偶现精度异常，固定--randomly-seed=1767963664必现精度异常-org-issues-AtomGit | GitCode (#41933)


| 字段 | 内容 |
|------|------|
| 问题 | [Bug]:CPU后端trace算子偶现精度异常，固定--randomly-seed=1767963664必现精度异常 |
| 根因 | mindspore的trace cpu算子走fp16存在精度累积问题，与x86上的tf的fp32计算精度存在误差。 |
| 修复 | x86环境trace pynative cpu算子的fp16版本精度与tf的fp32精度无法对上，重新提升精度至fp32处理后转换回fp16。 |
| 引入类型 | 测试新增测试场景 |
| 后端 | - |
| 状态 | DONE |

**关键教训**: mindspore的trace cpu算子走fp16存在精度累积问题，与x86上的tf的fp32计算精度存在误差。


### Case CS-032: mint.nn.functional.embedding/mint.nn.Embedding ascend存在精度问题-org-issues-AtomGit | GitCode (#41972)


| 字段 | 内容 |
|------|------|
| 问题 | pangu_sigma2.3编译耗时优化未达预期 |
| 根因 | > 1、 2.3上某些pass相比于2.2版本的实现，存在性能劣化 > 2、 2.3版本把trace功能下掉了，导致前端编译劣化 > |
| 修复 | > 1、修复性能劣化的前端图优化pass > 2、通过支持boost infer功能把trace功能下掉导致的性能劣化拿回来 > |
| 引入类型 | 特性合入引入 / Bugfix修复引入 / 测试新增测试场景 / 测试漏测 / 用例未适配 / 环境问题 / CANN升级 |
| 后端 | - |
| 状态 | DONE |

**关键教训**: > 1、 2.3上某些pass相比于2.2版本的实现，存在性能劣化 > 2、 2.3版本把trace功能下掉了，导致前端编译劣化 >


### Case CS-033: ops.pow fp32存在精度问题-org-issues-AtomGit | GitCode (#41932)


| 字段 | 内容 |
|------|------|
| 问题 | pangu_sigma2.3编译耗时优化未达预期 |
| 根因 | > 1、 2.3上某些pass相比于2.2版本的实现，存在性能劣化 > 2、 2.3版本把trace功能下掉了，导致前端编译劣化 > |
| 修复 | > 1、修复性能劣化的前端图优化pass > 2、通过支持boost infer功能把trace功能下掉导致的性能劣化拿回来 > |
| 引入类型 | 特性合入引入 / Bugfix修复引入 / 测试新增测试场景 / 测试漏测 / 用例未适配 / 环境问题 / CANN升级 |
| 后端 | - |
| 状态 | DONE |

**关键教训**: > 1、 2.3上某些pass相比于2.2版本的实现，存在性能劣化 > 2、 2.3版本把trace功能下掉了，导致前端编译劣化 >


### Case CS-034: 动态图rope utils仅与静态图pynative分支对齐精度，未与静态图master分支对齐-org-issues-AtomGit | GitCode (#41922)


| 字段 | 内容 |
|------|------|
| 问题 | 动态图rope_utils仅与静态图pynative分支对齐精度，未与静态图master分支对齐 |
| 根因 | 1、 动态图rope_utils仅与静态图pynative分支对齐精度，未与静态图master分支对齐 |
| 修复 | 1、重新与与静态图pynative分支对齐精度 |
| 引入类型 | 特性合入引入 |
| 后端 | - |
| 状态 | DONE |

**关键教训**: 1、 动态图rope_utils仅与静态图pynative分支对齐精度，未与静态图master分支对齐


### Case CS-035: mint.nn.Linear fp16 910a偶现精度问题-org-issues-AtomGit | GitCode (#41968)


| 字段 | 内容 |
|------|------|
| 问题 | pangu_sigma2.3编译耗时优化未达预期 |
| 根因 | > 1、 2.3上某些pass相比于2.2版本的实现，存在性能劣化 > 2、 2.3版本把trace功能下掉了，导致前端编译劣化 > |
| 修复 | > 1、修复性能劣化的前端图优化pass > 2、通过支持boost infer功能把trace功能下掉导致的性能劣化拿回来 > |
| 引入类型 | 特性合入引入 / Bugfix修复引入 / 测试新增测试场景 / 测试漏测 / 用例未适配 / 环境问题 / CANN升级 |
| 后端 | - |
| 状态 | DONE |

**关键教训**: > 1、 2.3上某些pass相比于2.2版本的实现，存在性能劣化 > 2、 2.3版本把trace功能下掉了，导致前端编译劣化 >


## 反向传播


### Case BP-021: if while for中使用常量tensor，反向报错RuntimeError: Can't access data on Ascend-org-issues-AtomGit | GitCode (#42166)


| 字段 | 内容 |
|------|------|
| 问题 | if_while_for中使用常量tensor，反向报错RuntimeError: Can't access data on Ascend |
| 根因 | 图编译下infer value流程需要正确输入cpu tensor，已完成host侧计算结果，并常量折叠。但当前版本的图编译流程并未在infer value前校验输入是否同步到host。 |
| 修复 | 新增可触发infer value的算子输入常量device tensor。 |
| Fix PR | [!91981](https://gitee.com/mindspore/mindspore/pulls/91981) |
| 引入类型 | 用例未适配 |
| 后端 | Ascend |
| 状态 | DONE |

**关键教训**: 图编译下infer value流程需要正确输入cpu tensor，已完成host侧计算结果，并常量折叠。但当前版本的图编译流程并未在infer value前校验输入是否同步到host。


### Case BP-022: lite删除minddata相关内容后，端侧使用RunStep方式时build报错Unsupported parameter type in Create : BinaryCrossEntropyGrad-org-issues-AtomGit | GitCode (#41976)


| 字段 | 内容 |
|------|------|
| 问题 | MindSporeTest在执行RunStep用例的时候报错Unsupported parameter type in Create : BinaryCrossEntropyGrad |
| 根因 | 测试用例编译出来的test_basic_predict没有链接mindspore-lite-train这个so，导致CreateTrainSession没有被注册到CreateTrainSessionCallbackHolder中，导致该算子没有被注册 |
| 修复 | 1、在测试用例的CMakeLists.txt的链接阶段针对mindspore-lite-train增加--no-as-needed选项，强制链接mindspore-lite-train |
| 引入类型 | 优化重构引入 |
| 后端 | - |
| 状态 | DONE |

**关键教训**: 测试用例编译出来的test_basic_predict没有链接mindspore-lite-train这个so，导致CreateTrainSession没有被注册到CreateTrainSession...


### Case BP-023: acosh算子设置01，并将设置和不设置context.set context(graph kernel flags="--disable expand ops=AcoshExt")的图对比，反向传播计算时报错RuntimeError: Unknown scalar type 1-org-issues-AtomGit | GitCode (#41967)


| 字段 | 内容 |
|------|------|
| 问题 | pangu_sigma2.3编译耗时优化未达预期 |
| 根因 | > 1、 2.3上某些pass相比于2.2版本的实现，存在性能劣化 > 2、 2.3版本把trace功能下掉了，导致前端编译劣化 > |
| 修复 | > 1、修复性能劣化的前端图优化pass > 2、通过支持boost infer功能把trace功能下掉导致的性能劣化拿回来 > |
| 引入类型 | 特性合入引入 / Bugfix修复引入 / 测试新增测试场景 / 测试漏测 / 用例未适配 / 环境问题 / CANN升级 |
| 后端 | - |
| 状态 | DONE |

**关键教训**: > 1、 2.3上某些pass相比于2.2版本的实现，存在性能劣化 > 2、 2.3版本把trace功能下掉了，导致前端编译劣化 >


## Shape推导


### Case SP-021: 构造GetNext动态shape网络多次执行的场景,用例执行时间从十分钟内涨至15分钟以上，导致用例被杀-org-issues-AtomGit | GitCode (#41951)


| 字段 | 内容 |
|------|------|
| 问题 | pangu_sigma2.3编译耗时优化未达预期 |
| 根因 | > 1、 2.3上某些pass相比于2.2版本的实现，存在性能劣化 > 2、 2.3版本把trace功能下掉了，导致前端编译劣化 > |
| 修复 | > 1、修复性能劣化的前端图优化pass > 2、通过支持boost infer功能把trace功能下掉导致的性能劣化拿回来 > |
| Fix PR | [!1](https://gitee.com/mindspore/mindspore/pulls/1) |
| 引入类型 | 特性合入引入 / Bugfix修复引入 / 测试新增测试场景 / 测试漏测 / 用例未适配 / 环境问题 / CANN升级 |
| 后端 | Ascend |
| 状态 | DONE |

**关键教训**: > 1、 2.3上某些pass相比于2.2版本的实现，存在性能劣化 > 2、 2.3版本把trace功能下掉了，导致前端编译劣化 >


### Case SP-022: 门禁用例失败：test nsa compress attention.py::test nsa compress attention dynamic shape TEST OP 报错：AssertionError-org-issues-AtomGit | GitCode (#41956)


| 字段 | 内容 |
|------|------|
| 问题 | pangu_sigma2.3编译耗时优化未达预期 |
| 根因 | > 1、 2.3上某些pass相比于2.2版本的实现，存在性能劣化 > 2、 2.3版本把trace功能下掉了，导致前端编译劣化 > |
| 修复 | > 1、修复性能劣化的前端图优化pass > 2、通过支持boost infer功能把trace功能下掉导致的性能劣化拿回来 > |
| 引入类型 | 特性合入引入 / Bugfix修复引入 / 测试新增测试场景 / 测试漏测 / 用例未适配 / 环境问题 / CANN升级 |
| 后端 | - |
| 状态 | DONE |

**关键教训**: > 1、 2.3上某些pass相比于2.2版本的实现，存在性能劣化 > 2、 2.3版本把trace功能下掉了，导致前端编译劣化 >


## Kernel实现


### Case KR-021: O1, 自动并行，8p模式，SplitFlattenMulDenseConstantNet， 偶现core在SetMsInternalEnableCustomKernelList-org-issues-AtomGit | GitCode (#41935)


| 字段 | 内容 |
|------|------|
| 问题 | 训练用例偶现SetMsInternalEnalbeCustomKernelList段错误 |
| 根因 | 1. MindSpore新版本支持多线程，原来这个函数没有多线程保护，支持多线程后，有概率会同时修改内部的set结构造成段错误; 训练用例不应该走到推理流程中，由于判断optional使用不对，不是判断是否推理模式，而是只要有值就会走到SetMsInternalEnableCustomKernelList函数中。 |
| 修复 | 1. 训练用例走进推理流程修改optional使用，判断取值value后判断; 多线程风险后续补充相关自建issue跟踪解决 |
| 引入类型 | 特性合入引入 |
| 后端 | - |
| 状态 | DONE |

**关键教训**: 1. MindSpore新版本支持多线程，原来这个函数没有多线程保护，支持多线程后，有概率会同时修改内部的set结构造成段错误; 训练用例不应该走到推理流程中，由于判断optional使用不对，不是判...


### Case KR-022: Cell实例中使用属性引用异常场景，非Parameter类型数据修改（syntax white list）, 报错RuntimeError: Output idx 0 of node @kernel graph2:CNode 5{[0]: ValueNode<Primitive> PrimFunc Assign-org-issues-AtomGit | GitCode (#41943)


| 字段 | 内容 |
|------|------|
| 问题 | pangu_sigma2.3编译耗时优化未达预期 |
| 根因 | > 1、 2.3上某些pass相比于2.2版本的实现，存在性能劣化 > 2、 2.3版本把trace功能下掉了，导致前端编译劣化 > |
| 修复 | > 1、修复性能劣化的前端图优化pass > 2、通过支持boost infer功能把trace功能下掉导致的性能劣化拿回来 > |
| 引入类型 | 特性合入引入 / Bugfix修复引入 / 测试新增测试场景 / 测试漏测 / 用例未适配 / 环境问题 / CANN升级 |
| 后端 | - |
| 状态 | DONE |

**关键教训**: > 1、 2.3上某些pass相比于2.2版本的实现，存在性能劣化 > 2、 2.3版本把trace功能下掉了，导致前端编译劣化 >


## 编译器/IR


### Case IR-021: ops.expm1/ops.log1p报错RuntimeError: When convert scalar to tensor, the scalar type: Complex128/Complex64 is invalid.-org-issues-AtomGit | GitCode (#41954)


| 字段 | 内容 |
|------|------|
| 问题 | pangu_sigma2.3编译耗时优化未达预期 |
| 根因 | > 1、 2.3上某些pass相比于2.2版本的实现，存在性能劣化 > 2、 2.3版本把trace功能下掉了，导致前端编译劣化 > |
| 修复 | > 1、修复性能劣化的前端图优化pass > 2、通过支持boost infer功能把trace功能下掉导致的性能劣化拿回来 > |
| 引入类型 | 特性合入引入 / Bugfix修复引入 / 测试新增测试场景 / 测试漏测 / 用例未适配 / 环境问题 / CANN升级 |
| 后端 | - |
| 状态 | DONE |

**关键教训**: > 1、 2.3上某些pass相比于2.2版本的实现，存在性能劣化 > 2、 2.3版本把trace功能下掉了，导致前端编译劣化 >


### Case IR-022: 【自提单】【MindFormers】【Mcore】静态图YarnRotaryEmbedding初始化与父类入参无法对应，初始化顺序有误-org-issues-AtomGit | GitCode (#41960)


| 字段 | 内容 |
|------|------|
| 问题 | pangu_sigma2.3编译耗时优化未达预期 |
| 根因 | > 1、 2.3上某些pass相比于2.2版本的实现，存在性能劣化 > 2、 2.3版本把trace功能下掉了，导致前端编译劣化 > |
| 修复 | > 1、修复性能劣化的前端图优化pass > 2、通过支持boost infer功能把trace功能下掉导致的性能劣化拿回来 > |
| 引入类型 | 特性合入引入 / Bugfix修复引入 / 测试新增测试场景 / 测试漏测 / 用例未适配 / 环境问题 / CANN升级 |
| 后端 | - |
| 状态 | DONE |

**关键教训**: > 1、 2.3上某些pass相比于2.2版本的实现，存在性能劣化 > 2、 2.3版本把trace功能下掉了，导致前端编译劣化 >


### Case IR-023: 【自提单】【MIndformers】【训练】动态图attention中含有transformer config中已经删除的参数导致训练报错-org-issues-AtomGit | GitCode (#41921)


| 字段 | 内容 |
|------|------|
| 问题 | pangu_sigma2.3编译耗时优化未达预期 |
| 根因 | > 1、 2.3上某些pass相比于2.2版本的实现，存在性能劣化 > 2、 2.3版本把trace功能下掉了，导致前端编译劣化 > |
| 修复 | > 1、修复性能劣化的前端图优化pass > 2、通过支持boost infer功能把trace功能下掉导致的性能劣化拿回来 > |
| 引入类型 | 特性合入引入 / Bugfix修复引入 / 测试新增测试场景 / 测试漏测 / 用例未适配 / 环境问题 / CANN升级 |
| 后端 | - |
| 状态 | DONE |

**关键教训**: > 1、 2.3上某些pass相比于2.2版本的实现，存在性能劣化 > 2、 2.3版本把trace功能下掉了，导致前端编译劣化 >


### Case IR-024: nn.adam ascend后端计算结果与标杆不一致-org-issues-AtomGit | GitCode (#41934)


| 字段 | 内容 |
|------|------|
| 问题 | pangu_sigma2.3编译耗时优化未达预期 |
| 根因 | > 1、 2.3上某些pass相比于2.2版本的实现，存在性能劣化 > 2、 2.3版本把trace功能下掉了，导致前端编译劣化 > |
| 修复 | > 1、修复性能劣化的前端图优化pass > 2、通过支持boost infer功能把trace功能下掉导致的性能劣化拿回来 > |
| 引入类型 | 特性合入引入 / Bugfix修复引入 / 测试新增测试场景 / 测试漏测 / 用例未适配 / 环境问题 / CANN升级 |
| 后端 | - |
| 状态 | DONE |

**关键教训**: > 1、 2.3上某些pass相比于2.2版本的实现，存在性能劣化 > 2、 2.3版本把trace功能下掉了，导致前端编译劣化 >


### Case IR-025: 门禁用例报错test qwen3 dryrun.py::test qwen3 cell dp2mp4pp2vpp4op 1f1b,test qwen3 dryrun.py::test qwen3 dp4mp4pp1op recompute-org-issues-AtomGit | GitCode (#41965)


| 字段 | 内容 |
|------|------|
| 问题 | pangu_sigma2.3编译耗时优化未达预期 |
| 根因 | > 1、 2.3上某些pass相比于2.2版本的实现，存在性能劣化 > 2、 2.3版本把trace功能下掉了，导致前端编译劣化 > |
| 修复 | > 1、修复性能劣化的前端图优化pass > 2、通过支持boost infer功能把trace功能下掉导致的性能劣化拿回来 > |
| 引入类型 | 特性合入引入 / Bugfix修复引入 / 测试新增测试场景 / 测试漏测 / 用例未适配 / 环境问题 / CANN升级 |
| 后端 | - |
| 状态 | DONE |

**关键教训**: > 1、 2.3上某些pass相比于2.2版本的实现，存在性能劣化 > 2、 2.3版本把trace功能下掉了，导致前端编译劣化 >


### Case IR-026: msrun rank id重排失败-org-issues-AtomGit | GitCode (#41924)


| 字段 | 内容 |
|------|------|
| 问题 | pangu_sigma2.3编译耗时优化未达预期 |
| 根因 | > 1、 2.3上某些pass相比于2.2版本的实现，存在性能劣化 > 2、 2.3版本把trace功能下掉了，导致前端编译劣化 > |
| 修复 | > 1、修复性能劣化的前端图优化pass > 2、通过支持boost infer功能把trace功能下掉导致的性能劣化拿回来 > |
| 引入类型 | 特性合入引入 / Bugfix修复引入 / 测试新增测试场景 / 测试漏测 / 用例未适配 / 环境问题 / CANN升级 |
| 后端 | - |
| 状态 | DONE |

**关键教训**: > 1、 2.3上某些pass相比于2.2版本的实现，存在性能劣化 > 2、 2.3版本把trace功能下掉了，导致前端编译劣化 >


### Case IR-027: tensor.mul 参数other类型校验丢失-org-issues-AtomGit | GitCode (#42116)


| 字段 | 内容 |
|------|------|
| 问题 | pangu_sigma2.3编译耗时优化未达预期 |
| 根因 | > 1、 2.3上某些pass相比于2.2版本的实现，存在性能劣化 > 2、 2.3版本把trace功能下掉了，导致前端编译劣化 > |
| 修复 | > 1、修复性能劣化的前端图优化pass > 2、通过支持boost infer功能把trace功能下掉导致的性能劣化拿回来 > |
| 引入类型 | 特性合入引入 / Bugfix修复引入 / 测试新增测试场景 / 测试漏测 / 用例未适配 / 环境问题 / CANN升级 |
| 后端 | - |
| 状态 | DONE |

**关键教训**: > 1、 2.3上某些pass相比于2.2版本的实现，存在性能劣化 > 2、 2.3版本把trace功能下掉了，导致前端编译劣化 >


### Case IR-028: O1 matmul 半自动并行 输入策略：[a, b], [b, c]， 输出策略：[a, c*b]， 偶现core-org-issues-AtomGit | GitCode (#41961)


| 字段 | 内容 |
|------|------|
| 问题 | pangu_sigma2.3编译耗时优化未达预期 |
| 根因 | > 1、 2.3上某些pass相比于2.2版本的实现，存在性能劣化 > 2、 2.3版本把trace功能下掉了，导致前端编译劣化 > |
| 修复 | > 1、修复性能劣化的前端图优化pass > 2、通过支持boost infer功能把trace功能下掉导致的性能劣化拿回来 > |
| 引入类型 | 特性合入引入 / Bugfix修复引入 / 测试新增测试场景 / 测试漏测 / 用例未适配 / 环境问题 / CANN升级 |
| 后端 | - |
| 状态 | DONE |

**关键教训**: > 1、 2.3上某些pass相比于2.2版本的实现，存在性能劣化 > 2、 2.3版本把trace功能下掉了，导致前端编译劣化 >


### Case IR-029: imod的input和other是5维时，正向e2e性能没有达到标杆的1.2倍-org-issues-AtomGit | GitCode (#41930)


| 字段 | 内容 |
|------|------|
| 问题 | pangu_sigma2.3编译耗时优化未达预期 |
| 根因 | > 1、 2.3上某些pass相比于2.2版本的实现，存在性能劣化 > 2、 2.3版本把trace功能下掉了，导致前端编译劣化 > |
| 修复 | > 1、修复性能劣化的前端图优化pass > 2、通过支持boost infer功能把trace功能下掉导致的性能劣化拿回来 > |
| 引入类型 | 特性合入引入 / Bugfix修复引入 / 测试新增测试场景 / 测试漏测 / 用例未适配 / 环境问题 / CANN升级 |
| 后端 | - |
| 状态 | DONE |

**关键教训**: > 1、 2.3上某些pass相比于2.2版本的实现，存在性能劣化 > 2、 2.3版本把trace功能下掉了，导致前端编译劣化 >


### Case IR-030: ops.scatternd pynative模式参数校验丢失-org-issues-AtomGit | GitCode (#41971)


| 字段 | 内容 |
|------|------|
| 问题 | pangu_sigma2.3编译耗时优化未达预期 |
| 根因 | > 1、 2.3上某些pass相比于2.2版本的实现，存在性能劣化 > 2、 2.3版本把trace功能下掉了，导致前端编译劣化 > |
| 修复 | > 1、修复性能劣化的前端图优化pass > 2、通过支持boost infer功能把trace功能下掉导致的性能劣化拿回来 > |
| 引入类型 | 特性合入引入 / Bugfix修复引入 / 测试新增测试场景 / 测试漏测 / 用例未适配 / 环境问题 / CANN升级 |
| 后端 | - |
| 状态 | DONE |

**关键教训**: > 1、 2.3上某些pass相比于2.2版本的实现，存在性能劣化 > 2、 2.3版本把trace功能下掉了，导致前端编译劣化 >


### Case IR-031: 自定义算子asdfft在旧CANN包报错找不到libasdsip.so路径-org-issues-AtomGit | GitCode (#41945)


| 字段 | 内容 |
|------|------|
| 问题 | pangu_sigma2.3编译耗时优化未达预期 |
| 根因 | > 1、 2.3上某些pass相比于2.2版本的实现，存在性能劣化 > 2、 2.3版本把trace功能下掉了，导致前端编译劣化 > |
| 修复 | > 1、修复性能劣化的前端图优化pass > 2、通过支持boost infer功能把trace功能下掉导致的性能劣化拿回来 > |
| 引入类型 | 特性合入引入 / Bugfix修复引入 / 测试新增测试场景 / 测试漏测 / 用例未适配 / 环境问题 / CANN升级 |
| 后端 | - |
| 状态 | DONE |

**关键教训**: > 1、 2.3上某些pass相比于2.2版本的实现，存在性能劣化 > 2、 2.3版本把trace功能下掉了，导致前端编译劣化 >


### Case IR-032: 门禁用例报错test ops group cases.py::test reduction op group case level0,test ops group cases.py::test unary op group case level0-org-issues-AtomGit | GitCode (#41913)


| 字段 | 内容 |
|------|------|
| 问题 | pangu_sigma2.3编译耗时优化未达预期 |
| 根因 | > 1、 2.3上某些pass相比于2.2版本的实现，存在性能劣化 > 2、 2.3版本把trace功能下掉了，导致前端编译劣化 > |
| 修复 | > 1、修复性能劣化的前端图优化pass > 2、通过支持boost infer功能把trace功能下掉导致的性能劣化拿回来 > |
| 引入类型 | 特性合入引入 / Bugfix修复引入 / 测试新增测试场景 / 测试漏测 / 用例未适配 / 环境问题 / CANN升级 |
| 后端 | Ascend |
| 状态 | DONE |

**关键教训**: > 1、 2.3上某些pass相比于2.2版本的实现，存在性能劣化 > 2、 2.3版本把trace功能下掉了，导致前端编译劣化 >


### Case IR-033: mindone开启编译缓存报错：SetScalarToAttributeProto ir] Unsupported scalar type: FP16Imm-org-issues-AtomGit | GitCode (#41927)


| 字段 | 内容 |
|------|------|
| 问题 | pangu_sigma2.3编译耗时优化未达预期 |
| 根因 | > 1、 2.3上某些pass相比于2.2版本的实现，存在性能劣化 > 2、 2.3版本把trace功能下掉了，导致前端编译劣化 > |
| 修复 | > 1、修复性能劣化的前端图优化pass > 2、通过支持boost infer功能把trace功能下掉导致的性能劣化拿回来 > |
| 引入类型 | 特性合入引入 / Bugfix修复引入 / 测试新增测试场景 / 测试漏测 / 用例未适配 / 环境问题 / CANN升级 |
| 后端 | - |
| 状态 | DONE |

**关键教训**: > 1、 2.3上某些pass相比于2.2版本的实现，存在性能劣化 > 2、 2.3版本把trace功能下掉了，导致前端编译劣化 >


### Case IR-034: mint.nn.PixelShuffle 报错 RuntimeError: Invalid abstract;AbstractProblem-org-issues-AtomGit | GitCode (#41973)


| 字段 | 内容 |
|------|------|
| 问题 | DeadNode节点遗留到后端出现报错。 |
| 根因 | 前端脚本发生变化，导致构图发生变化，需要新增pass适配 |
| 修复 | 新增switch_simplify pass，避免DeadNode节点遗留到后端出现报错。 |
| 引入类型 | 测试漏测 |
| 后端 | - |
| 状态 | DONE |

**关键教训**: 前端脚本发生变化，导致构图发生变化，需要新增pass适配


### Case IR-035: [Bug]deepseek网络，eod泛化场景，并行策略dp1mp1pp16ep1bs1mb16gas1，跑测版本和以往版本，相同场景，loss绝对误差和norm相对误差超0；跑测版本相同版本，确定性可以固定住-org-issues-AtomGit | GitCode (#41977)


| 字段 | 内容 |
|------|------|
| 问题 | pangu_sigma2.3编译耗时优化未达预期 |
| 根因 | > 1、 2.3上某些pass相比于2.2版本的实现，存在性能劣化 > 2、 2.3版本把trace功能下掉了，导致前端编译劣化 > |
| 修复 | > 1、修复性能劣化的前端图优化pass > 2、通过支持boost infer功能把trace功能下掉导致的性能劣化拿回来 > |
| 引入类型 | 特性合入引入 / Bugfix修复引入 / 测试新增测试场景 / 测试漏测 / 用例未适配 / 环境问题 / CANN升级 |
| 后端 | - |
| 状态 | DONE |

**关键教训**: > 1、 2.3上某些pass相比于2.2版本的实现，存在性能劣化 > 2、 2.3版本把trace功能下掉了，导致前端编译劣化 >


### Case IR-036: linux aarch64+ascend910b，python310环境。Build时配置的卡和Tensor的卡ID不一致，推理输出卡ID变为Tensor卡ID，跨卡推理失败。-org-issues-AtomGit | GitCode (#41958)


| 字段 | 内容 |
|------|------|
| 问题 | pangu_sigma2.3编译耗时优化未达预期 |
| 根因 | > 1、 2.3上某些pass相比于2.2版本的实现，存在性能劣化 > 2、 2.3版本把trace功能下掉了，导致前端编译劣化 > |
| 修复 | > 1、修复性能劣化的前端图优化pass > 2、通过支持boost infer功能把trace功能下掉导致的性能劣化拿回来 > |
| 引入类型 | 特性合入引入 / Bugfix修复引入 / 测试新增测试场景 / 测试漏测 / 用例未适配 / 环境问题 / CANN升级 |
| 后端 | - |
| 状态 | DONE |

**关键教训**: > 1、 2.3上某些pass相比于2.2版本的实现，存在性能劣化 > 2、 2.3版本把trace功能下掉了，导致前端编译劣化 >


### Case IR-037: 自定义算子在旧CANN包执行报错RuntimeError: Error building extension 'my ops'-org-issues-AtomGit | GitCode (#41948)


| 字段 | 内容 |
|------|------|
| 问题 | pangu_sigma2.3编译耗时优化未达预期 |
| 根因 | > 1、 2.3上某些pass相比于2.2版本的实现，存在性能劣化 > 2、 2.3版本把trace功能下掉了，导致前端编译劣化 > |
| 修复 | > 1、修复性能劣化的前端图优化pass > 2、通过支持boost infer功能把trace功能下掉导致的性能劣化拿回来 > |
| 引入类型 | 特性合入引入 / Bugfix修复引入 / 测试新增测试场景 / 测试漏测 / 用例未适配 / 环境问题 / CANN升级 |
| 后端 | - |
| 状态 | DONE |

**关键教训**: > 1、 2.3上某些pass相比于2.2版本的实现，存在性能劣化 > 2、 2.3版本把trace功能下掉了，导致前端编译劣化 >


### Case IR-038: linux x86 64 cpu环境编译lite encrypt pre inference版本包，报错找不到头文件#include "nlohmann/json.hpp"-org-issues-AtomGit | GitCode (#41969)


| 字段 | 内容 |
|------|------|
| 问题 | linux_x86_64_cpu环境编译lite encrypt_pre_inference版本包，报错找不到头文件#include "nlohmann/json.hpp" |
| 根因 | 特性合入导致的问题，合入PR: [https://gitee.com/mindspore/mindspore-lite/pulls/484](https://gitee.com/mindspore/mindspore-lite/pulls/484) |
| 修复 | 1)修复非云侧场景编包时引入所需要的第三方库的依赖 |
| 引入类型 | 特性合入引入 |
| 后端 | - |
| 状态 | DONE |

**关键教训**: 特性合入导致的问题，合入PR: [https://gitee.com/mindspore/mindspore-lite/pulls/484](https://gitee.com/mindspore/m...


### Case IR-039: Morph内部调用的函数包含*args, **kwargs入参时报错-org-issues-AtomGit | GitCode (#41959)


| 字段 | 内容 |
|------|------|
| 问题 | pangu_sigma2.3编译耗时优化未达预期 |
| 根因 | > 1、 2.3上某些pass相比于2.2版本的实现，存在性能劣化 > 2、 2.3版本把trace功能下掉了，导致前端编译劣化 > |
| 修复 | > 1、修复性能劣化的前端图优化pass > 2、通过支持boost infer功能把trace功能下掉导致的性能劣化拿回来 > |
| 引入类型 | 特性合入引入 / Bugfix修复引入 / 测试新增测试场景 / 测试漏测 / 用例未适配 / 环境问题 / CANN升级 |
| 后端 | - |
| 状态 | DONE |

**关键教训**: > 1、 2.3上某些pass相比于2.2版本的实现，存在性能劣化 > 2、 2.3版本把trace功能下掉了，导致前端编译劣化 >


### Case IR-040: 门禁用例报错test functional method.py::test method too many parameters tests/st/compiler/functional overload-org-issues-AtomGit | GitCode (#41949)


| 字段 | 内容 |
|------|------|
| 问题 | pangu_sigma2.3编译耗时优化未达预期 |
| 根因 | > 1、 2.3上某些pass相比于2.2版本的实现，存在性能劣化 > 2、 2.3版本把trace功能下掉了，导致前端编译劣化 > |
| 修复 | > 1、修复性能劣化的前端图优化pass > 2、通过支持boost infer功能把trace功能下掉导致的性能劣化拿回来 > |
| 引入类型 | 特性合入引入 / Bugfix修复引入 / 测试新增测试场景 / 测试漏测 / 用例未适配 / 环境问题 / CANN升级 |
| 后端 | - |
| 状态 | DONE |

**关键教训**: > 1、 2.3上某些pass相比于2.2版本的实现，存在性能劣化 > 2、 2.3版本把trace功能下掉了，导致前端编译劣化 >


## API/签名


### Case API-021: deepseek sft 网络加载权重时报错：RuntimeError: Error(s) in loading state dict for GPTModel-org-issues-AtomGit | GitCode (#42184)


| 字段 | 内容 |
|------|------|
| 问题 | deepseek sft 网络加载权重时报错：RuntimeError: Error(s) in loading state_dict for GPTModel |
| 根因 | MindSpeed-LLM仓master分支transformer_impl参数的默认值逻辑删除，需要在模型脚本里添加--transformer-impl local入参 |
| 修复 | 1、在mindspore模型脚本里添加--transformer-impl local入参 |
| 引入类型 | 特性合入引入 |
| 后端 | Ascend |
| 状态 | DONE |

**关键教训**: MindSpeed-LLM仓master分支transformer_impl参数的默认值逻辑删除，需要在模型脚本里添加--transformer-impl local入参


### Case API-022: 【自提单】num floating point operations接口需要补充ut用例-org-issues-AtomGit | GitCode (#42154)


| 字段 | 内容 |
|------|------|
| 问题 | num_floating_point_operations接口需要补充ut用例 |
| 根因 | 1、 num_floating_point_operations接口缺少用例，覆盖率较低 |
| 修复 | 1、增加接口用例，达到全场景覆盖 |
| 引入类型 | 特性合入引入 |
| 后端 | - |
| 状态 | DONE |

**关键教训**: 1、 num_floating_point_operations接口缺少用例，覆盖率较低


### Case API-023: deepseek pretrain 网络加载权重时训练失败，报错：AssertionError: transformer engine does not support ascend coc-org-issues-AtomGit | GitCode (#42183)


| 字段 | 内容 |
|------|------|
| 问题 | deepseek pretrain 网络加载权重时训练失败，报错：AssertionError: transformer engine does not support ascend coc |
| 根因 | MindSpeed-LLM仓master分支transformer_impl参数的默认值逻辑删除，需要在模型脚本里添加--transformer-impl local入参 |
| 修复 | 1、在mindspore模型脚本里添加--transformer-impl local入参 |
| 引入类型 | 特性合入引入 |
| 后端 | Ascend |
| 状态 | DONE |

**关键教训**: MindSpeed-LLM仓master分支transformer_impl参数的默认值逻辑删除，需要在模型脚本里添加--transformer-impl local入参


### Case API-024: 部分进程创建通信组用例因为python升级超时报错-org-issues-AtomGit | GitCode (#41926)


| 字段 | 内容 |
|------|------|
| 问题 | 异常用例，在非rank_list的进程中调用`mindspore.communication.create_group`接口创建通信组会出现coredump。 |
| 根因 | 更新python版本3.10 -> 3.12。 |
| 修复 | 修改异常通过thow value_error的方式抛出。  # |
| 引入类型 | 测试新增测试场景 |
| 后端 | - |
| 状态 | DONE |

**关键教训**: 更新python版本3.10 -> 3.12。


## 运行时


### Case RT-021: 版本用例执行失败：test hal memory.py::test runtime max memory allocated-org-issues-AtomGit | GitCode (#41942)


| 字段 | 内容 |
|------|------|
| 问题 | 用例执行失败 |
| 根因 | 由于门禁精准触发无法触发910A，且用例还是LEVEL1不会跑，导致代码语法问题没有被门禁识别 |
| 修复 | 修复语法问题 |
| 引入类型 | 特性合入引入 |
| 后端 | - |
| 状态 | DONE |

**关键教训**: 由于门禁精准触发无法触发910A，且用例还是LEVEL1不会跑，导致代码语法问题没有被门禁识别


## 性能退化


### Case PF-021: [Bug]ascend910B4环境上unet conv3d.onnx使能aoe转换生成mindir模型后推理性能劣化-org-issues-AtomGit | GitCode (#41950)


| 字段 | 内容 |
|------|------|
| 问题 | 历史看护模型性能劣化 |
| 根因 | 1、CANN包更新，conv算子性能劣化 |
| 修复 | 1、更新CANN包 |
| 引入类型 | CANN升级 |
| 后端 | - |
| 状态 | DONE |

**关键教训**: 1、CANN包更新，conv算子性能劣化


## 其他


### Case OT-021: 单机验证pipeline,使用global norm算法, dp=1,开启优化器并行+多副本, 使用@lazy inline报错：TypeError: 'module' object is not callable-org-issues-AtomGit | GitCode (#42129)


| 字段 | 内容 |
|------|------|
| 问题 | import mindspore.common.lazy_inline as lazy_inline，使用@lazy_inline报错：TypeError: 'module' object is not callable |
| 根因 | ``` # 重构前common/__init__.py，同名模块被import时，从包命名空间直接获取同名方法 from mindspore.common.lazy_inline import lazy_inline |
| 修复 | 用例适配  import mindspore.common.lazy_inline as lazy_inline  ——>  ①from mindspore import lazy_inline  ②from mindspore.graph.lazy_inline import lazy_inline |
| 引入类型 | 用例未适配 |
| 后端 | Ascend |
| 状态 | DONE |

**关键教训**: ``` # 重构前common/__init__.py，同名模块被import时，从包命名空间直接获取同名方法 from mindspore.common.lazy_inline import laz...


### Case OT-022: 门禁用例报错test clamp.py::test clamp overload error report[1]-org-issues-AtomGit | GitCode (#41940)


| 字段 | 内容 |
|------|------|
| 问题 | 报错与预期不一致 |
| 根因 | 报错不一致 |
| 修复 | 用例拆分到对应动静态图对应重载模块异常场景测试文件处，抛异常内容进行对应适配  动态图：tests/st/tensor/overload/test_parse_exception.py  静态图：tests/st/compiler/functional_overload/test_functional_method.py |
| 引入类型 | Bugfix修复引入 |
| 后端 | - |
| 状态 | DONE |

**关键教训**: 报错不一致


### Case OT-023: infer类推理算子报错The current operator needs to be supplemented with an adapter.-org-issues-AtomGit | GitCode (#41941)


| 字段 | 内容 |
|------|------|
| 问题 | 在CANN20250428、20250724版本。infer类推理算子报错The current operator needs to be supplemented with an adapter. |
| 根因 | 1、 老CANN包中缺少symbol: aclrtGetResInCurrentThread，算子库因升级了atb源码依赖这个。所以无法兼容8.3之前的CANN包 |
| 修复 | 1、无法兼容，ccb评审，评审结论如下：  昇腾计算联合CCB结论20250120：vllm-mindspore推理配套不在昇腾计算推理解决方案中维护，可以自行决定配套与兼容关系。我们当前客户整体使用vllm-mindspore的配套发布件，r2.7.1之后mindspore版本推理不兼容CANN 8.2.0.RC1影响可控。 |
| 引入类型 | 测试新增测试场景 |
| 后端 | - |
| 状态 | DONE |

**关键教训**: 1、 老CANN包中缺少symbol: aclrtGetResInCurrentThread，算子库因升级了atb源码依赖这个。所以无法兼容8.3之前的CANN包


### Case OT-024: nn.sgd ascend报错Memcpy async failed, stream is not in current ctx-org-issues-AtomGit | GitCode (#41937)


| 字段 | 内容 |
|------|------|
| 问题 | [Bug]:nn.sgd ascend报错Memcpy async failed, stream is not in current ctx |
| 根因 | torch_npu版本升级后，原本跑在CPU的torch对比用例执行在了npu上，这样同一进程内同时执行torch_npu和ms,导致ms执行报错 |
| 修复 | 不涉及 |
| 引入类型 | 用例未适配 |
| 后端 | - |
| 状态 | DONE |

**关键教训**: torch_npu版本升级后，原本跑在CPU的torch对比用例执行在了npu上，这样同一进程内同时执行torch_npu和ms,导致ms执行报错


### Case OT-025: TensorDump位于网络中间位置, 且在循环外, 半自动并行, net中存在循环, mode设置为"all" 偶现core-org-issues-AtomGit | GitCode (#41952)


| 字段 | 内容 |
|------|------|
| 问题 | 执行用例偶现core |
| 根因 | 1、 系统不支持多线程并发设置或读取环境变量 |
| 修复 | 1、删除可能存在全局变量并发设置的操作; 适配用例。避免多次调用通信初始化接口，以及避免将环境变量相关设置操作放在通信初始化之前。 |
| 引入类型 | 测试漏测 |
| 后端 | - |
| 状态 | DONE |

**关键教训**: 1、 系统不支持多线程并发设置或读取环境变量


### Case OT-026: [Bug] 盘古 38bv3网络，训练失败报错：AttributeError: 'NoneType' object has no attribute 'item'-org-issues-AtomGit | GitCode (#41946)


| 字段 | 内容 |
|------|------|
| 问题 | ms改动导致网络报错 |
| 根因 | 1、 二分确认，ms改动引起，0106ms包必现，0107不复现 |
| 修复 | 1、0107ms包不复现 |
| 引入类型 | Bugfix修复引入 |
| 后端 | - |
| 状态 | DONE |

**关键教训**: 1、 二分确认，ms改动引起，0106ms包必现，0107不复现


### Case OT-027: [Bug] 盘古vlm网络 开确定性 8p，训练失败报错：RuntimeError: Lazy Async copy failed. -org-issues-AtomGit | GitCode (#41947)


| 字段 | 内容 |
|------|------|
| 问题 | 开同步后的真实报错：vlm网络报错SyncStream failed for op aclnnIndexPutImpl |
| 根因 | 1、 二分定位到是cann引入的问题（疑似cann相关的环境问题）。 |
| 修复 | 1、问题不复现 |
| 引入类型 | CANN升级 |
| 后端 | - |
| 状态 | DONE |

**关键教训**: 1、 二分定位到是cann引入的问题（疑似cann相关的环境问题）。
