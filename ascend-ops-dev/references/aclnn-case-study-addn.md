# `aclnnAddN` 封装经验

这份案例总结用于提醒：`aclnn` 封装问题通常不是“补两个接口函数”这么简单，重点在于辨清真实执行链路和最小修复边界。

## 1. 先区分 4 条路径

分析 AddN 时，必须分清：

- 现网 `aclOp` 路径
- 新增 `aclnn` L2 路径
- L0 路径
- built-in TBE / AICPU / 本地 AscendC AICore kernel 路径

不要把这些路径混成“同一个 AddN 实现”。

## 2. `aclOp` 正常不代表本地源码链路正常

AddN 的经验表明：

- 现网 `aclOp` 很可能走 `canndev` built-in TBE/GE 路径
- 新补的 `aclnn` 可能直接命中本地 `ops-math` 里的 L0/AICore 路径

因此：

- “`aclOp` 没问题”不能证明“本地 kernel 没问题”
- “新增 `aclnn` 后才暴露问题”不等于“`aclnn` 代码本身有 bug”

## 3. 目标能力要先收敛

AddN 最终确认的能力边界是：

- 对齐 L0 真实能力
- 不支持广播
- 输入 tensor 的 shape 和 dtype 必须一致
- 不额外开放新 dtype，只对齐既有可执行能力

这类判断必须基于真实执行能力，而不是只看 host infer 文案或上层期望。

## 4. 什么时候才改 kernel

只有同时满足下面条件，才建议对 kernel/tiling 做最小修复：

1. `aclnn/L0` 已明确命中当前源码中的本地实现
2. 实机或 smoke 已经稳定复现问题
3. 问题会阻断用户要求的既有能力对齐目标

如果只是理论猜测，或者问题只存在于未要求支持的 dtype/场景，不要贸然扩改 kernel。

## 5. AddN 常用验证清单

### 5.1 代码侧

- `tests/ut/op_api/test_aclnn_add_n.cpp`
- `examples/test_aclnn_add_n.cpp`
- `tests/smoke/*add_n*`

### 5.2 场景侧

- `nullptr`
- 空输入列表
- 输入项为空
- 单输入
- 多输入
- dtype 不一致
- shape 不一致
- 关键成功 dtype
- 典型失败 case

## 6. 远端环境验证习惯

用户已给出远端环境时，优先直接按环境复现：

```bash
cd /home/lch/work
source env_ms.sh
```

再做：

- 单算子 `opapi` 编译
- 定向 UT
- smoke
- example

## 7. 交付文档必须写清楚的点

- 为什么 AddN 不支持广播
- 为什么某些 dtype 不支持，依据是什么
- 为什么需要或不需要 kernel 修复
- 为什么 `aclOp` 与 `aclnn` 的暴露行为不同
- 哪些结论来自实测，哪些只是代码分析推论
