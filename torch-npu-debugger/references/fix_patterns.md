# torch_npu 常见修复模式

## 目录

1. [ACLNN 算子适配修复](#1-aclnn-算子适配修复)
2. [Format 处理修复](#2-format-处理修复)
3. [dtype 转换修复](#3-dtype-转换修复)
4. [算子注册修复](#4-算子注册修复)
5. [反向传播修复](#5-反向传播修复)
6. [运行时修复](#6-运行时修复)
7. [版本配套与环境修复](#7-版本配套与环境修复)
8. [自定义算子与 ATB 修复](#8-自定义算子与-atb-修复)
9. [非连续 tensor 修复](#9-非连续-tensor-修复)
10. [ACL API 边界保护](#10-acl-api-边界保护)
11. [Optimizer 测试兼容性修复](#11-optimizer-测试兼容性修复)
12. [ONNX 测试兼容性修复](#12-onnx-测试兼容性修复)

---

## 1. ACLNN 算子适配修复

### 1.1 添加 DO_COMPATIBILITY fallback

**问题**: 新 ACLNN 接口在旧 CANN 版本上不存在，导致 `undefined symbol`。

**修复**: 添加 DO_COMPATIBILITY 宏，回退到 aclops 实现。

```cpp
// op_plugin/ops/opapi/XxxKernelNpu.cpp

// Before: no fallback
at::Tensor xxx_npu(const at::Tensor& self) {
    auto result = npu_preparation::apply_tensor(self);
    EXEC_NPU_CMD(aclnnXxx, self, result);
    return result;
}

// After: add DO_COMPATIBILITY fallback
at::Tensor xxx_npu(const at::Tensor& self) {
    DO_COMPATIBILITY(aclnnXxx, acl_op::xxx_npu(self));

    auto result = npu_preparation::apply_tensor(self);
    EXEC_NPU_CMD(aclnnXxx, self, result);
    return result;
}
```

### 1.2 修复 ACLNN 参数不匹配

**问题**: aclnn 接口签名变更，参数数量或类型不匹配。

**修复**: 对齐 CANN 头文件中的函数签名。

```cpp
// Before: old signature
EXEC_NPU_CMD(aclnnXxx, self, other, result);

// After: new signature adds alpha parameter
EXEC_NPU_CMD(aclnnXxx, self, other, alpha, result);
```

### 1.3 添加 Workspace 处理

**问题**: ACLNN 算子需要额外 workspace 但未分配。

**修复**: 使用 EXEC_NPU_CMD 宏（自动处理 workspace），或手动分配。

```cpp
// EXEC_NPU_CMD automatically handles workspace via GetWorkspaceSize + Execute
// If manual control is needed:
uint64_t ws_size = 0;
aclnnXxxGetWorkspaceSize(self_desc, result_desc, &ws_size, &executor);
void* ws_addr = nullptr;
if (ws_size > 0) {
    auto ws_tensor = at::empty({static_cast<int64_t>(ws_size)}, self.options().dtype(at::kByte));
    ws_addr = ws_tensor.data_ptr();
}
aclnnXxx(ws_addr, ws_size, executor, stream);
```

### 1.4 语义不一致场景下的定向 fallback

**问题**: 上游 PyTorch 语义明确，旧 ACLOP 路径可以支持，但 ACLNN 在特定语义场景下报错、编译失败或行为不一致。

**适用场景**:
- CPU 行为明确且可复现
- ACLOP 路径正常
- ACLNN 路径在同样输入下异常
- 问题集中在 `dim=None`、`keepdim=True`、shape 推导、dtype 语义或边界输入处理等语义场景

**修复**: 保留默认 ACLNN 路径，但对已知不兼容语义做显式 fallback 到 `acl_op::*`，同时在注释中写明原因，并整理问题单材料推动底层修复。

**注意**:
- 这种 fallback 属于规避方案，不等于底层问题已解决。
- 必须在定位总结里明确记录：CPU / ACLOP / ACLNN 三方对比结论。
- 若确认是 ACLNN 缺陷，应同步输出问题单模板与简版摘要，方便向底层提单。
- 问题单中必须详细写清复现过程：环境、复现命令、最小脚本、实际结果、期望结果，以及是否需要关闭 fallback 才能复现原始 ACLNN 问题。
- 详细问题单建议固定使用以下一级标题：环境信息、复现步骤、最小复现脚本、实际结果、期望结果、对比结论、torch_npu 当前规避方式。

---

## 2. Format 处理修复

### 2.1 强制基础格式输入

**问题**: 算子不支持 NZ/FRACTAL_Z 等私有格式输入。

**修复**: 在算子入口处转换为基础格式。

```cpp
// Before: directly use input (may be in NZ format)
at::Tensor xxx_npu(const at::Tensor& self) {
    auto result = npu_preparation::apply_tensor(self);
    EXEC_NPU_CMD(aclnnXxx, self, result);
    return result;
}

// After: ensure base format input
at::Tensor xxx_npu(const at::Tensor& self) {
    DO_COMPATIBILITY(aclnnXxx, acl_op::xxx_npu(self));

    at::Tensor self_cp = self;
    if (!at_npu::native::FormatHelper::IsBaseFormatType(self)) {
        self_cp = at_npu::native::custom_ops::npu_format_cast(self, ACL_FORMAT_ND);
    }
    auto result = npu_preparation::apply_tensor_without_format(self_cp);
    EXEC_NPU_CMD(aclnnXxx, self_cp, result);
    return result;
}
```

### 2.2 使用 apply_tensor_without_format

**问题**: `apply_tensor` 会继承输入的 format，导致输出 format 不正确。

**修复**: 使用 `apply_tensor_without_format` 创建基础格式输出。

```cpp
// Before: inherits input format (may cause issues)
auto result = npu_preparation::apply_tensor(self);

// After: always use base format for output
auto result = npu_preparation::apply_tensor_without_format(output_size, self.options());
```

### 2.3 修复非连续张量

**问题**: 非连续张量传入 ACLNN 导致计算错误。

**修复**: 在算子入口处确保张量连续。

```cpp
at::Tensor xxx_npu(const at::Tensor& self) {
    at::Tensor self_cp = self.is_contiguous() ? self : self.contiguous();
    // ... proceed with self_cp
}
```

---

## 3. dtype 转换修复

### 3.1 添加 dtype 提升

**问题**: NPU fp16 精度不足导致计算溢出。

**修复**: 将输入提升到 float32 计算后再转回。

```cpp
at::Tensor xxx_npu(const at::Tensor& self) {
    DO_COMPATIBILITY(aclnnXxx, acl_op::xxx_npu(self));

    // Promote to float32 for precision
    bool need_cast = (self.scalar_type() == at::kHalf || self.scalar_type() == at::kBFloat16);
    at::Tensor self_cp = need_cast ? self.to(at::kFloat) : self;

    auto result = npu_preparation::apply_tensor_without_format(self_cp);
    EXEC_NPU_CMD(aclnnXxx, self_cp, result);

    // Cast back to original dtype
    return need_cast ? result.to(self.scalar_type()) : result;
}
```

### 3.2 修复 dtype 推导

**问题**: 输出 dtype 推导错误，使用了错误的 dtype。

**修复**: 显式指定输出 dtype。

```cpp
// Before: wrong dtype inference
auto result = npu_preparation::apply_tensor(self);

// After: explicit dtype
auto result = npu_preparation::apply_tensor_without_format(
    output_size, self.options().dtype(at::kFloat));
```

### 3.3 处理 bool 类型

**问题**: NPU 不支持 bool 类型的某些运算。

**修复**: 将 bool 转为 int 计算后转回。

```cpp
at::Tensor xxx_npu(const at::Tensor& self) {
    if (self.scalar_type() == at::kBool) {
        auto self_int = self.to(at::kInt);
        auto result = xxx_npu(self_int);
        return result.to(at::kBool);
    }
    // ... normal path
}
```

---

## 4. 算子注册修复

### 4.1 添加算子注册

**问题**: 算子未注册到 PrivateUse1 dispatch key。

**修复**: 在 TORCH_LIBRARY_IMPL 中添加注册。

```cpp
// In the appropriate registration file
TORCH_LIBRARY_IMPL(aten, PrivateUse1, m) {
    m.impl("xxx", TORCH_FN(op_plugin::xxx_npu));
    m.impl("xxx.out", TORCH_FN(op_plugin::xxx_out_npu));
}
```

### 4.2 添加 Autograd 注册

**问题**: 算子有 forward 实现但缺少 autograd 注册，导致 backward 失败。

**修复**: 注册到 AutogradPrivateUse1。

```cpp
TORCH_LIBRARY_IMPL(aten, AutogradPrivateUse1, m) {
    m.impl("xxx", TORCH_FN(op_plugin::xxx_autograd));
}
```

### 4.3 修复 DO_COMPATIBILITY 注册

**问题**: DO_COMPATIBILITY 回退到 aclops 但 aclops 命名空间中没有对应实现。

**修复**: 确保 aclops 中有对应实现，或提供内联 fallback。

```cpp
// Option 1: ensure aclops implementation exists
DO_COMPATIBILITY(aclnnXxx, acl_op::xxx_npu(self, other));

// Option 2: inline fallback when no aclops implementation
DO_COMPATIBILITY(aclnnXxx, [&]() {
    // Fallback implementation using OpCommand
    at_npu::native::OpCommand cmd;
    cmd.Name("Xxx").Input(self).Input(other).Output(result).Run();
    return result;
}());
```

---

## 5. 反向传播修复

### 5.1 修复 backward 函数

**问题**: backward 实现中 dtype 或 shape 处理错误。

**修复**: 确保 grad 的 dtype 和 shape 与 forward 输出一致。

```cpp
at::Tensor xxx_backward_npu(const at::Tensor& grad_output, const at::Tensor& self) {
    DO_COMPATIBILITY(aclnnXxxBackward, acl_op::xxx_backward_npu(grad_output, self));

    // Ensure grad has correct dtype
    at::Tensor grad = grad_output.scalar_type() == self.scalar_type()
        ? grad_output
        : grad_output.to(self.scalar_type());

    auto grad_input = npu_preparation::apply_tensor_without_format(self);
    EXEC_NPU_CMD(aclnnXxxBackward, grad, self, grad_input);
    return grad_input;
}
```

### 5.2 添加缺失的 backward

**问题**: 算子只有 forward 没有 backward，导致 autograd 失败。

**修复**: 实现 backward 并注册到 AutogradPrivateUse1。

```cpp
// 1. Implement backward in opapi/
at::Tensor xxx_backward_npu(const at::Tensor& grad, const at::Tensor& self) {
    DO_COMPATIBILITY(aclnnXxxBackward, acl_op::xxx_backward_npu(grad, self));
    auto grad_input = npu_preparation::apply_tensor_without_format(self);
    EXEC_NPU_CMD(aclnnXxxBackward, grad, self, grad_input);
    return grad_input;
}

// 2. Create autograd function
class XxxFunction : public torch::autograd::Function<XxxFunction> {
    static at::Tensor forward(torch::autograd::AutogradContext* ctx,
                              const at::Tensor& self) {
        ctx->save_for_backward({self});
        return op_plugin::xxx_npu(self);
    }
    static torch::autograd::variable_list backward(
        torch::autograd::AutogradContext* ctx,
        torch::autograd::variable_list grad_outputs) {
        auto saved = ctx->get_saved_variables();
        return {op_plugin::xxx_backward_npu(grad_outputs[0], saved[0])};
    }
};
```

---

## 6. 运行时修复

### 6.1 添加 Stream 同步

**问题**: 异步执行导致数据竞争或结果不正确。

**修复**: 在关键点添加 stream 同步。

```cpp
// Add synchronization after critical operations
c10_npu::NPUStream stream = c10_npu::getCurrentNPUStream();
aclrtSynchronizeStream(stream);
```

### 6.2 修复内存分配

**问题**: 输出 tensor 大小计算错误导致内存越界。

**修复**: 修正 output size 计算。

```cpp
// Before: wrong output size
auto output_size = {self.size(0), self.size(1)};

// After: correct output size calculation
auto output_size = op_infer::broadcast_ops_npu_output_size(self, other);
auto result = npu_preparation::apply_tensor_without_format(output_size, self.options());
```

### 6.3 修复设备检查

**问题**: 输入张量在不同设备上导致运行时错误。

**修复**: 添加设备一致性检查。

```cpp
at::Tensor xxx_npu(const at::Tensor& self, const at::Tensor& other) {
    TORCH_CHECK(self.device() == other.device(),
        "Expected all tensors to be on the same device, but found at least two devices, ",
        self.device(), " and ", other.device());
    // ...
}
```

---

## 7. 版本配套与环境修复

### 7.1 op-plugin submodule 对齐

**问题**: 大量 `undefined reference to op_api::*`，op-plugin commit 与 torch_npu tag 不匹配。

**修复**: 对齐 submodule 版本。

```bash
# Check current submodule status
git submodule status

# Reset to the correct commit for this torch_npu version
git submodule update --init --recursive
```

### 7.2 GCC ABI 不匹配

**问题**: `undefined symbol` 含 `cxx11`，torch 与 torch_npu 的 GCC ABI 版本不一致。该场景通常是 **预编译 wheel / ABI 标记不匹配**，而不是“本地重编后 import 阶段直接 native crash”。

**诊断**:

```python
# Check torch's GCC version for ABI mismatch hints
import torch
print(torch.__config__.show())
# Combine this with wheel tag / manylinux information when diagnosing prebuilt package mismatch
```

**修复**: 重新下载与 torch GCC ABI 匹配的 torch_npu whl 包。若是本地重编后的 `import torch_npu` / `_c10d_npu_init` 直接 `SIGSEGV`，不要停留在 wheel ABI 检查，继续按 7.3 的 `.comment` 工具链诊断执行。

### 7.3 Python / torch / torch_npu 工具链不兼容

**问题**: `import torch_npu`、`_c10d_npu_init` 或 pybind 绑定阶段直接 `SIGSEGV`。同一 Python 环境下旧包正常、重编包崩溃，且 `libpython`、`torch/_C`、good 包和 bad 包的编译器版本不同。

**诊断**:

```bash
# Compare Python, torch, and torch_npu compiler comments
# Replace <good-torch-npu-path> / <bad-torch-npu-path> with the actual package roots.
# In this incident they were torch_npu-- and torch_npu respectively.
readelf -p .comment /root/miniconda3/envs/lch_py310/lib/libpython3.10.so
readelf -p .comment /root/miniconda3/envs/lch_py310/lib/python3.10/site-packages/torch/_C.cpython-310-aarch64-linux-gnu.so
readelf -p .comment <good-torch-npu-path>/_C.cpython-310-aarch64-linux-gnu.so
readelf -p .comment <bad-torch-npu-path>/_C.cpython-310-aarch64-linux-gnu.so

# Check Python build toolchain
python - <<'PY'
import platform, sysconfig
print(platform.python_compiler())
print(sysconfig.get_config_var('CC'))
print(sysconfig.get_config_var('CXX'))
print(sysconfig.get_config_var('LDSHARED'))
PY
```

**判断模式**:
- 如果 Python / `libpython` / `torch/_C` / good 包为 GCC 11.x，而 bad 包为 GCC 10.x，优先判定为构建工具链不兼容。
- 如果宿主机默认 `gcc --version` 为 10.x，但 good 包 `.comment` 为 11.2.1，应继续检查容器内是否存在 `gcc-toolset-11` 或其他隐藏构建环境。
- 如果 GCC 11 只存在于 Docker overlay 或容器文件系统，不要在宿主机直接调用这些编译器二进制；它们通常依赖容器内 glibc、libisl、libstdc++ 等运行库，脱离原上下文会引入新的动态库错误。

**修复**: 回到与 good 包一致的 GCC 11.x 构建上下文（通常是容器内的 gcc-toolset-11）做 clean rebuild，再复现 import 行为验证是否消除崩溃。

### 7.4 C++ 标准修复

**问题**: `is_convertible_v was not declared`，C++ 标准被降级为 C++14。

**修复**: 修改 CMakeLists.txt 和 setup.py。

```cmake
# CMakeLists.txt: change C++14 back to C++17
set(CMAKE_CXX_STANDARD 17)
```

```python
# setup.py: change extra_compile_args
extra_compile_args = ['-std=c++17']
```

### 7.5 容器内 GCC 11 clean rebuild

**问题**: 服务器宿主机默认 GCC 为 10.x，但好包由容器内 `gcc-toolset-11` 构建，宿主机直接重编会引入 import 阶段崩溃。

**修复**: 在原容器构建上下文内执行 clean rebuild，不要从宿主机直接复用 overlay 编译器。

```bash
# Discover gcc-toolset-11 inside running container
ssh user@server "docker exec <container> bash -lc 'which gcc g++ && gcc --version | head -1 && g++ --version | head -1'"

# Build inside the same container/toolchain context
ssh user@server "docker exec <container> bash -lc '
  cd /home/lch/work && source env_ms.sh mindspore/ && cd torch_npu && \
  rm -rf build dist && bash ci/build.sh --python=3.10
'"
```

**注意**:
- clean rebuild 前先确认容器中看到的 GCC 版本与 good 包 `.comment` 一致。
- 如果只是从 `/home/_docker/overlay2/.../merged/.../g++` 直接在宿主机调用，常见失败是 `libisl.so` 缺失或 `glibc` 私有符号错误；这种失败不能证明源码有问题，只能说明工具链脱离了原运行时上下文。

---

## 8. 自定义算子与 ATB 修复

### 8.1 ATB dtype 对齐

**问题**: ATB 算子 "setup failed"，dtype 组合不合法（如 `torch.long` 应为 `torch.int32`）。

**修复**: 对齐 dtype 到 ATB 支持的组合。

```python
# Before: ATB does not support int64 for block_table
block_table = torch.randint(0, 10, (batch, max_blocks), dtype=torch.long).npu()

# After: use int32
block_table = torch.randint(0, 10, (batch, max_blocks), dtype=torch.int32).npu()
```

### 8.2 gen_opapi out dtype 动态推断

**问题**: `gen_opapi` 配置中 `out` 的 dtype 硬编码为 `at::kFloat`，但输入是 `float16`，导致 MTE 越界（`0x800000`）。

**修复**: out dtype 应动态推断或与输入对齐。

```cpp
// Before: hardcoded dtype
auto result = npu_preparation::apply_tensor_without_format(
    {x.size(0), y.size(1)}, x.options().dtype(at::kFloat));

// After: use input dtype
auto result = npu_preparation::apply_tensor_without_format(
    {x.size(0), y.size(1)}, x.options());
```

### 8.3 opapi infershape 修复

**问题**: ACLNN 报 `161002` + `CheckAxisRange/CheckShapeValid failed`，输出 tensor 的 size 计算有误。

**修复**: 修正 opapi 中输出 tensor 的 size/shape 计算逻辑。

```cpp
// Before: wrong output size when num_classes != -1
auto output_size = op_infer::array_to_small_vector(self.sizes());

// After: correct output size calculation
auto output_size = op_infer::array_to_small_vector(self.sizes());
if (num_classes != -1) {
    output_size.push_back(num_classes);
}
```

---

## 9. 非连续 tensor 修复

### 9.1 out 参数非连续写入

**问题**: `xxx.out` 在 `out` tensor 非连续且 shape 不等时，写入位置计算错误。

**修复**: 在写入前确保 out tensor 连续，或修正写入逻辑。

```cpp
// Before: directly write to non-contiguous out
EXEC_NPU_CMD(aclnnXxx, self, result);

// After: ensure contiguous or use a temporary buffer
at::Tensor result_contiguous = result.is_contiguous() ? result :
    npu_preparation::apply_tensor_without_format(result.sizes(), result.options());
EXEC_NPU_CMD(aclnnXxx, self, result_contiguous);
if (!result.is_contiguous()) {
    result.copy_(result_contiguous);
}
```

---

## 10. ACL API 边界保护

### 10.1 外部返回值上界保护

**问题**: ACL API 返回的 count/size 直接用作循环上界，可能导致越界。

**修复**: 添加 MAX 上界保护。

```cpp
// Before: trust external value
for (size_t i = 0; i < moduleCount; i++) { ... }

// After: add upper bound protection
constexpr size_t MAX_MODULE_NUM = 1024;
for (size_t i = 0; i < std::min(moduleCount, MAX_MODULE_NUM); i++) { ... }
```

---

## 11. Optimizer 测试兼容性修复

### 11.1 state_dict 空 state 守卫

**问题**: 测试代码直接用 `state_dict["state"][0]` 访问 optimizer state，但某些 optimizer 配置下（如 SGD `momentum=0`）state 为空字典，导致 `KeyError`。上游 PyTorch 测试用 `.values()` 迭代天然兼容空字典，torch_npu 的测试移植时未做防护。

**根因**: PyTorch SGD 在 `momentum=0`（默认值）时不写入 `self.state`，`state_dict()["state"]` 返回 `{}`。

**修复**: 在访问 `state_dict["state"][0]` 前添加非空检查。

```python
# Before: crashes when state is empty
if "step" in state_dict["state"][0] and torch.is_tensor(
    state_dict["state"][0]["step"]
):

# After: guard against empty state
if state_dict["state"] and "step" in state_dict["state"][0] and torch.is_tensor(
    state_dict["state"][0]["step"]
):
```

**适用场景**: `test/optim/test_optim.py` 中 `_test_state_dict` 方法，以及任何直接按 key 访问 optimizer state 的测试代码。

**排查要点**: 当 optimizer 测试出现 `KeyError` 且 key 为整数时，优先检查 optimizer 是否在当前配置下会产生空 state（如无 momentum 的 SGD、无 state 的自定义 optimizer）。

---

## 12. ONNX 测试兼容性修复

### 12.1 ONNX Runtime bfloat16 算术运算不支持

**问题**: torch_npu ONNX 测试 `test_arithmetic_bfp16` 失败，错误信息：
```
NotImplemented: [ONNXRuntimeError] : 9 : NOT_IMPLEMENTED : Could not find an implementation for Add(14)
```

**根因分析**:
1. **ONNX Runtime CPU 限制**: ONNX Runtime CPUExecutionProvider 不支持 bfloat16 的 Add/Sub/Mul 等算术运算
2. **torch_npu 测试架构**: `test/onnx/onnx_test_common.py:370` 硬编码使用 `CPUExecutionProvider`
3. **无 NPU Provider**: ONNX Runtime 官方不支持 Ascend NPU，无 NPUExecutionProvider

**验证方法**:
```python
import onnxruntime as ort
print(ort.get_available_providers())
# ['AzureExecutionProvider', 'CPUExecutionProvider'] - 无 NPU provider

# 测试 ONNX Runtime CPU 对 bfloat16 的支持
import torch
import torch.nn as nn

class Arithmetic(nn.Module):
    def forward(self, x):
        y = torch.ones(3, 4, dtype=torch.bfloat16)
        x = x.type_as(y)
        return torch.mul(torch.add(x, y), torch.sub(x, y))  # 算术运算 - CPU 不支持

class CastOnly(nn.Module):
    def forward(self, x):
        y = torch.ones(3, 4, dtype=torch.bfloat16)
        return x.type_as(y).to(dtype=torch.float16)  # 仅 cast - CPU 支持
```

**修复方案**: 添加 skip 装饰器，当环境不支持时跳过测试。

**文件1**: `test/onnx/pytorch_test_common.py`

```python
skipIfONNXRuntimeNoBFloat16 = _skipper(
    lambda: True,
    "ONNX Runtime CPU does not support bfloat16 for Add/Sub/Mul ops",
)
```

**文件2**: `test/onnx/test_pytorch_onnx_onnxruntime_npu.py`

```python
import pytorch_test_common
from pytorch_test_common import (
    ...
    skipIfONNXRuntimeNoBFloat16,
    ...
)

@skipIfUnsupportedMinOpsetVersion(13)
@skipIfNoBFloat16NPU
@skipIfONNXRuntimeNoBFloat16  # 新增
 def test_arithmetic_bfp16(self):
    ...
```

**适用场景**:
- 测试使用 bfloat16 dtype 进行算术运算（Add/Sub/Mul/Div 等）
- ONNX Runtime 只能使用 CPUExecutionProvider
- 对比验证：PyTorch 官方 CUDA 测试在缺乏 GPU 时也会被跳过

**排查要点**:
1. 检查 ONNX Runtime 可用 providers：`onnxruntime.get_available_providers()`
2. 检查测试代码中 ONNX 后端配置位置：`onnx_test_common.py` 中 `InferenceSession` 的 `providers` 参数
3. 区分 cast 操作与算术运算：ONNX Runtime CPU 支持 bfloat16 cast，但不支持算术
4. 对比 PyTorch 官方测试：确认是否只在 CUDA 测试中存在，CPU 测试是否跳过

**长期解决方案**:
1. **华为提供 ONNX Runtime NPU Provider**: 开发 `onnxruntime-npu` 包支持 NPUExecutionProvider
2. **使用 REFERENCE backend**: 修改测试使用 `OnnxBackend.REFERENCE`，但数值验证可能失败（输出 NaN）
3. **仅验证导出**: 设置 `options.verify_data = False` 仅检查 ONNX 导出成功，不验证数值

**参考**:
- ONNX Runtime Execution Providers: https://onnxruntime.ai/docs/execution-providers/
- PyTorch 官方行为：PyTorch CUDA 测试在 `BFloat16 CUDA is not available` 时跳过

### 12.2 ONNX 与 protobuf 版本不兼容

**问题**: ONNX 测试运行时报错：
```
AttributeError: 'google._upb._message.FieldDescriptor' object has no attribute 'label'
```

**根因**: ONNX 1.17.0 与 protobuf 5.x+ 不兼容，`onnx.helper.strip_doc_string` 等函数依赖已移除的 protobuf API。

**修复方案**: 降级 protobuf 或升级 onnx。

```bash
# 方案1：降级 protobuf 到兼容版本（推荐）
pip install protobuf==4.25.3

# 方案2：升级 onnx 到修复版本
pip install onnx>=1.18.0
```

**验证修复**:
```python
import onnx
import io
from onnx import helper

# 测试 strip_doc_string 是否正常工作
model = onnx.ModelProto()
helper.strip_doc_string(model)
print("strip_doc_string: OK")
```

**适用场景**:
- `test_utility_funs.py` 中的 `test_verbose` 等使用 `strip_doc_string` 的测试
- 任何调用 `onnx.helper.strip_doc_string` 的代码
- 升级 protobuf 后 ONNX 相关功能异常

**排查要点**:
1. 检查 onnx 版本：`python -c "import onnx; print(onnx.__version__)"`
2. 检查 protobuf 版本：`python -c "import google.protobuf; print(google.protobuf.__version__)"`
3. 测试 `strip_doc_string` 是否正常工作
4. ONNX 1.17.0 + protobuf 5.x+ 组合必然触发此错误

---

## 13. 测试辅助文件缺失修复

### 13.1 测试文件同步时缺失辅助模块

**问题**: 运行测试时报错：
```
ModuleNotFoundError: No module named 'autograd_helper'
ModuleNotFoundError: No module named 'verify'
```

**根因**: 测试文件 `test_xxx.py` 从 PyTorch 同步时，未同步其依赖的辅助模块（如 `autograd_helper.py`, `verify.py` 等）。

**修复方案**: 从 PyTorch 官方仓库复制缺失的辅助文件。

**步骤**:

1. **确定缺失文件**: 根据报错信息确定缺失的模块名。

2. **查找 PyTorch 官方文件位置**:
```bash
# 在 PyTorch 源码中搜索
grep -r "from autograd_helper" pytorch/test/
grep -r "from verify" pytorch/test/

# 或直接查看测试文件导入
head -30 pytorch/test/onnx/test_utility_funs.py
```

3. **复制缺失文件到 torch_npu**:
```bash
# 常见缺失文件
pytorch/test/onnx/autograd_helper.py  -> torch_npu/test/onnx/
pytorch/test/onnx/verify.py           -> torch_npu/test/onnx/
pytorch/test/onnx/onnx_test_common.py -> torch_npu/test/onnx/
```

4. **验证修复**:
```bash
cd torch_npu/test/onnx
python -c "import autograd_helper; import verify; print('All modules imported successfully')"

# 运行原测试
python test_utility_funs.py -v -k test_verbose
```

**常见缺失文件清单**:

| 文件 | 用途 | 常见于 |
|------|------|--------|
| `autograd_helper.py` | 自定义 autograd 函数测试 | `test_utility_funs.py` |
| `verify.py` | ONNX 模型验证工具 | `test_utility_funs.py` |
| `onnx_test_common.py` | ONNX 测试公共基类 | 多个 ONNX 测试文件 |
| `pytorch_test_common.py` | PyTorch 测试公共工具 | 多个测试文件 |

**预防措施**:

同步 PyTorch 测试文件时，检查文件头部的所有 `from xxx import` 和 `import xxx` 语句，确保依赖的辅助模块也被同步。

**长期解决方案**:

1. **建立同步检查脚本**: 自动化检查测试文件的依赖完整性
2. **维护同步文档**: 记录每个同步测试文件的依赖关系
3. **CI 检查**: 在 CI 中运行所有测试，确保无模块缺失错误

**参考**:
- PyTorch 官方 test/onnx 目录: https://github.com/pytorch/pytorch/tree/main/test/onnx
