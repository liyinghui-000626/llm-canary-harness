# LLM Prompt/Model Canary Release Harness

## 架构评审文档

文档版本：V1.0  
文档日期：2026-05-02  
面向对象：架构师 / 技术负责人 / 平台负责人

---

## 1. 项目背景

随着 LLM 应用进入业务生产环境，Prompt、Model、RAG Pipeline、参数配置会频繁迭代。现有团队常见做法是直接替换线上配置，缺少稳定的灰度发布、链路追踪、基础指标观测、风险止损和复盘机制。

本项目拟建设一个面向 LLM 应用的 Canary Release Harness，作为模型调用链路外层的工程控制层，统一承担以下职责：

- 版本管理
- 灰度分流
- 请求级 Trace
- 基础指标采集
- 风险规则判断
- 自动回滚
- 人工确认扩量

第一阶段优先建设发布治理骨架，第二阶段再强化评测智能化能力。

---

## 2. 建设目标

### 2.1 V1 目标

V1 聚焦最小闭环，目标是先把 LLM 应用发布治理主链路跑通，做到：

- 可观测
- 可分流
- 可回滚
- 可人工确认扩量
- 可复盘

V1 不追求复杂质量评测，而是优先保证：

- 版本管理清晰
- 流量分配稳定
- 请求链路可追踪
- 基础指标准确
- 规则回滚可跑通

### 2.2 V2 目标

V2 在 V1 骨架稳定基础上，补强智能评测与决策能力，重点建设：

- 离线基准集评测
- 在线抽样评测
- LLM-as-Judge
- 质量评分可信度提升
- 更细粒度实验结论

---

## 3. 产品边界

### 3.1 V1 解决的问题

- 新旧 Prompt / Model / RAG 版本可管理
- 新版本可通过小流量灰度上线
- 同一用户在实验期间命中稳定版本
- 每个请求可追踪版本与执行链路
- 可按错误率、延迟、超时等护栏指标自动止损
- 系统可给出扩量建议，但扩量需要人工确认

### 3.2 V1 暂不解决的问题

- 高精度自动正确率判断
- 幻觉率的高可信自动判别
- 显著性统计分析
- 全自动扩量发布
- 多租户复杂权限体系

### 3.3 V2 重点解决的问题

- 新旧版本回答质量自动对比
- 在线请求抽样质量检测
- 基于规则 + Judge 的综合评估
- 更可信的发布建议与实验报告

---

## 4. 总体方案

### 4.1 总体定位

该系统不是一个单独的聊天应用，而是 LLM 应用发布治理平台。  
它不替代模型服务本身，而是包裹在模型调用链路外侧，为业务应用提供统一的发布控制、观测和回滚能力。

### 4.2 两阶段建设策略

#### V1：发布治理最小闭环

- 应用管理
- 版本管理
- 灰度实验管理
- 请求网关与稳定分流
- 基础指标采集
- 风险规则引擎
- 自动回滚
- 人工审批扩量
- 实验总览与请求 Trace

#### V2：评测智能化增强

- 离线评测任务
- 在线抽样评测
- LLM-as-Judge
- 格式合法性检查
- 证据一致性评测
- 实验质量报告增强

---

## 5. V1 重点能力设计

## 5.1 应用与版本管理

### 功能目标

将 Prompt、Model、参数、RAG 配置统一抽象为版本对象，支持线上版本清晰管理。

### 核心能力

- 创建应用
- 创建版本
- 从已有版本复制新版本
- 查看版本详情
- 对比版本差异
- 标记稳定版本
- 管理版本状态流转

### 版本对象建议字段

- `version_id`
- `app_id`
- `version_name`
- `base_version_id`
- `prompt_template`
- `model_name`
- `endpoint_url`
- `temperature`
- `top_p`
- `max_tokens`
- `rag_enabled`
- `rag_config`
- `output_schema`
- `status`
- `created_by`
- `created_at`

### 状态流转

`draft -> testing -> canary -> stable -> deprecated`

说明：

- `draft`：草稿态，不接受真实流量
- `testing`：测试验证中
- `canary`：灰度实验中
- `stable`：当前稳定版本
- `deprecated`：废弃版本

### 设计原则

- 线上版本不可直接覆盖修改
- 任何上线变更都以新版本对象承载
- 实验必须绑定明确版本号
- 稳定版本和实验版本分离管理

---

## 5.2 灰度实验管理

### 功能目标

支持对照版本和实验版本在线灰度对比，控制新版本流量规模，并为后续回滚和扩量提供实验容器。

### 核心能力

- 创建实验
- 选择对照组与实验组
- 配置流量比例
- 配置规则护栏
- 启动实验
- 停止实验
- 查看实验状态
- 审批扩量

### 实验核心字段

- `experiment_id`
- `app_id`
- `experiment_name`
- `control_version_id`
- `treatment_version_id`
- `traffic_control`
- `traffic_treatment`
- `status`
- `auto_rollback`
- `start_time`
- `end_time`

### 建议初始形态

- 单应用同一时刻仅允许一个运行中主实验
- 默认采用 A/B 双版本对比
- 首轮灰度建议 `90/10`
- 系统支持后续从 `10% -> 30% -> 50%` 扩量，但需人工确认

---

## 5.3 请求网关与稳定分流

### 功能目标

所有业务请求统一进入网关，由平台完成版本路由、模型调用编排和链路记录。

### 处理流程

1. 接收业务请求
2. 根据 `app_id` 查询当前实验
3. 按实验规则判断命中版本
4. 加载版本配置
5. 调用对应 Prompt / Model / RAG 流程
6. 返回结果
7. 记录请求日志与 Trace

### V1 分流规则

#### 规则一：按比例稳定分流

基于 `user_id hash` 实现固定桶分流，确保同一用户在实验期间稳定命中同一版本。

示例：

```text
bucket = hash(user_id) % 100
if bucket < 10:
    version = treatment
else:
    version = control
```

#### 规则二：白名单分流

指定内部测试用户优先进入实验版本。

#### 规则三：按渠道分流

支持基于 `channel` 字段进行规则路由，例如 `web -> v2`，`app -> v1`。

### 设计原则

- 分流逻辑放在平台网关层，不侵入业务应用
- 流量命中理由必须可追踪
- 分流规则变更必须留痕
- 扩量后原有用户命中结果尽量保持稳定

---

## 5.4 请求链路追踪与基础可观测性

### 功能目标

建立基于请求事实日志的观测基础，为实验判断、回滚和复盘提供统一数据来源。

### 单次请求建议记录字段

- `request_id`
- `trace_id`
- `app_id`
- `experiment_id`
- `version_id`
- `user_id`
- `session_id`
- `query`
- `routing_reason`
- `model_name`
- `retrieval_docs`
- `input_tokens`
- `output_tokens`
- `total_tokens`
- `latency_ms`
- `cost`
- `status`
- `error_message`
- `created_at`

### V1 基础指标

- 请求量
- 成功率
- 错误率
- 平均延迟
- P95 延迟
- 输入 Token
- 输出 Token
- 单次调用成本
- 每版本请求分布
- 回滚触发次数

### V1 观测维度

- 按应用
- 按版本
- 按实验
- 按时间窗口
- 按渠道

### Dashboard 最小范围

#### 页面一：实验总览

- 当前实验状态
- 流量分配
- 风险等级
- 当前建议动作

#### 页面二：版本指标对比

- 请求量对比
- 错误率对比
- 延迟对比
- 成本对比

#### 页面三：请求 Trace 详情

- 请求命中实验
- 命中版本
- 路由原因
- 执行耗时
- 调用模型
- 错误原因

---

## 5.5 风险规则引擎

### 功能目标

基于基础运行指标执行护栏判断，输出“继续观察 / 建议扩量 / 自动回滚”三类结果。

### 关键设计原则

- 自动化只用于止损
- 扩量建议必须人工确认
- 决策结果必须可解释

### 规则分层

#### A. 硬护栏：触发自动回滚

适合直接止损的场景：

- 错误率 > 5%
- 平均延迟 > 对照组 1.5 倍
- 连续超时率显著升高
- 连续 N 分钟调用异常

#### B. 软规则：仅建议扩量

适合人工判断的场景：

- 样本量达到阈值
- 错误率未高于对照组
- 成本增幅在可接受范围
- 延迟稳定
- 连续观察窗口内指标无异常

### 决策输出结构

- `decision_type`: `rollback / keep_observing / recommend_expand`
- `risk_level`: `high / medium / low`
- `triggered_rules`
- `recommended_next_split`
- `requires_manual_approval`

### 示例

```json
{
  "decision_type": "recommend_expand",
  "risk_level": "low",
  "triggered_rules": [
    "sample_size_ready",
    "error_rate_stable",
    "latency_within_guardrail"
  ],
  "recommended_next_split": "70/30",
  "requires_manual_approval": true
}
```

---

## 5.6 自动回滚与人工审批扩量

### 功能目标

将系统自动止损与人工放量拆分设计，符合企业真实发布治理流程。

### 自动回滚处理流程

1. 停止当前实验
2. 将实验版本流量调整为 `0%`
3. 将稳定版本恢复为 `100%`
4. 更新实验状态为 `rollback`
5. 记录回滚日志
6. 发送通知

### 人工审批扩量流程

1. 规则引擎生成扩量建议
2. 页面展示建议依据和当前指标
3. 负责人发起审批确认
4. 审批通过后修改流量比例
5. 记录审批与操作日志

### 审批记录建议字段

- `approval_id`
- `experiment_id`
- `current_split`
- `recommended_split`
- `approved_by`
- `approval_reason`
- `approved_at`

### 设计原则

- 回滚是系统动作
- 扩量是人工动作
- 所有动作必须可审计、可回放

---

## 6. V1 最小闭环演示流程

建议作为架构评审与 Demo 验证主链路：

1. 创建一个 LLM 应用
2. 创建稳定版本 `v1`
3. 基于 `v1` 复制生成实验版本 `v2`
4. 创建一个 `90/10` 灰度实验
5. 业务请求进入网关并按 `user_id hash` 稳定分流
6. 平台记录每次请求的版本、延迟、错误、Token 和成本
7. 规则引擎定时汇总实验指标并输出结论
8. 若错误率或延迟异常，则自动回滚
9. 若指标稳定，则生成“建议扩量到 30%”
10. 负责人手工审批扩量

该流程即可证明平台具备：

- 可管理
- 可分流
- 可观测
- 可止损
- 可人工决策

---

## 7. V1 系统架构建议

### 7.1 逻辑架构

```text
业务应用
  |
  v
请求网关 / API Gateway
  |
  +-- 实验路由服务
  +-- 版本配置服务
  +-- LLM 执行编排服务
  +-- Trace / 日志记录
  |
  v
模型服务 / RAG 服务 / OpenAI-compatible Endpoint

后台任务层
  |
  +-- 指标聚合任务
  +-- 风险规则引擎
  +-- 自动回滚任务
  +-- 扩量建议任务

平台管理层
  |
  +-- 应用管理
  +-- 版本管理
  +-- 实验管理
  +-- Dashboard
  +-- 审批操作

数据层
  |
  +-- PostgreSQL
  +-- Redis
```

### 7.2 技术建议

#### 后端

- FastAPI
- SQLAlchemy
- Pydantic
- PostgreSQL
- Redis
- APScheduler 或 Celery

#### 前端

- Streamlit：适合快速搭建 Demo
- React + Ant Design：适合后续平台化

#### 模型接入

- OpenAI-compatible API
- vLLM
- Qwen / DeepSeek / OpenAI API

#### 可观测性

- 应用日志
- 请求 Trace
- Prometheus / Grafana 作为后续增强项

---

## 8. V1 数据模型建议

### 8.1 applications

```sql
CREATE TABLE applications (
    app_id VARCHAR PRIMARY KEY,
    app_name VARCHAR NOT NULL,
    app_type VARCHAR,
    description TEXT,
    owner VARCHAR,
    stable_version_id VARCHAR,
    status VARCHAR,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);
```

### 8.2 model_versions

```sql
CREATE TABLE model_versions (
    version_id VARCHAR PRIMARY KEY,
    app_id VARCHAR,
    version_name VARCHAR,
    base_version_id VARCHAR,
    prompt_template TEXT,
    model_name VARCHAR,
    endpoint_url TEXT,
    temperature FLOAT,
    top_p FLOAT,
    max_tokens INTEGER,
    rag_enabled BOOLEAN,
    rag_config JSON,
    output_schema JSON,
    status VARCHAR,
    created_by VARCHAR,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);
```

### 8.3 experiments

```sql
CREATE TABLE experiments (
    experiment_id VARCHAR PRIMARY KEY,
    app_id VARCHAR,
    experiment_name VARCHAR,
    control_version_id VARCHAR,
    treatment_version_id VARCHAR,
    traffic_control INTEGER,
    traffic_treatment INTEGER,
    status VARCHAR,
    auto_rollback BOOLEAN,
    start_time TIMESTAMP,
    end_time TIMESTAMP,
    created_at TIMESTAMP
);
```

### 8.4 request_logs

```sql
CREATE TABLE request_logs (
    request_id VARCHAR PRIMARY KEY,
    trace_id VARCHAR,
    experiment_id VARCHAR,
    app_id VARCHAR,
    version_id VARCHAR,
    user_id VARCHAR,
    session_id VARCHAR,
    query TEXT,
    answer TEXT,
    routing_reason VARCHAR,
    model_name VARCHAR,
    input_tokens INTEGER,
    output_tokens INTEGER,
    total_tokens INTEGER,
    latency_ms INTEGER,
    cost FLOAT,
    status VARCHAR,
    error_message TEXT,
    created_at TIMESTAMP
);
```

### 8.5 rollback_logs

```sql
CREATE TABLE rollback_logs (
    rollback_id VARCHAR PRIMARY KEY,
    experiment_id VARCHAR,
    from_version_id VARCHAR,
    to_version_id VARCHAR,
    trigger_rule VARCHAR,
    reason TEXT,
    operator VARCHAR,
    status VARCHAR,
    created_at TIMESTAMP
);
```

### 8.6 approval_logs

```sql
CREATE TABLE approval_logs (
    approval_id VARCHAR PRIMARY KEY,
    experiment_id VARCHAR,
    current_split VARCHAR,
    recommended_split VARCHAR,
    approved_by VARCHAR,
    approval_reason TEXT,
    status VARCHAR,
    created_at TIMESTAMP
);
```

---

## 9. 核心接口建议

### 9.1 应用与版本管理

- `POST /apps`
- `GET /apps`
- `POST /apps/{app_id}/versions`
- `GET /apps/{app_id}/versions`
- `GET /versions/{version_id}`
- `GET /versions/{version_id}/diff/{target_version_id}`

### 9.2 灰度实验

- `POST /experiments`
- `GET /experiments`
- `POST /experiments/{experiment_id}/start`
- `POST /experiments/{experiment_id}/stop`
- `POST /experiments/{experiment_id}/approve-expand`

### 9.3 请求执行

- `POST /gateway/invoke`

### 9.4 Trace 与指标

- `GET /experiments/{experiment_id}/metrics`
- `GET /requests/{request_id}`
- `GET /experiments/{experiment_id}/decision`

### 9.5 回滚

- `POST /experiments/{experiment_id}/rollback`

---

## 10. V2 增强方向

V2 建议在 V1 主链路稳定、数据采集可信后启动，重点建设以下能力：

### 10.1 离线评测

- 固定测试集
- 新旧版本批量回放
- 正确性评分
- 分类场景对比

### 10.2 在线抽样评测

- 从真实请求中按比例抽样
- 异步执行评测任务
- 回写评测结果

### 10.3 评测分层

#### L0：规则校验

- JSON 格式合法性
- 输出字段完整性
- 拒答率检查

#### L1：离线基准集评测

- correctness
- 场景分类得分

#### L2：在线智能评测

- faithfulness
- Judge 打分
- 人工抽检校准

### 10.4 智能报告

- 哪些问题类型提升
- 哪些问题类型退化
- 质量与成本是否同时可接受
- 是否具备扩量条件

---

## 11. 主要风险与控制建议

### 风险一：V1 范围失控

如果在 V1 过早引入复杂质量评测，项目会从“平台骨架建设”偏移到“评测算法建设”。

建议：

- V1 严格只做基础观测与规则护栏
- V2 再引入智能评测

### 风险二：指标口径不一致

若日志与聚合来源不一致，会导致回滚判断不可信。

建议：

- 统一以 `request_logs` 作为事实源
- 聚合任务只做派生计算

### 风险三：分流不稳定影响实验可信度

若同一用户多次请求命中版本变化，实验数据会失真。

建议：

- 使用稳定哈希桶
- 保留实验周期内分流一致性

### 风险四：自动扩量风险过高

企业通常不接受系统直接自动放量。

建议：

- 自动回滚
- 人工审批扩量
- 全量审计记录

---

## 12. 里程碑建议

### 里程碑一：V1 核心链路

- 应用管理
- 版本管理
- 灰度实验
- 请求网关
- 请求日志
- 指标聚合
- 自动回滚
- 人工扩量审批

### 里程碑二：V1 可视化与演示

- 实验总览
- 指标看板
- 请求 Trace 详情
- 回滚日志页

### 里程碑三：V2 智能评测

- 离线评测任务
- 在线抽样评测
- LLM-as-Judge
- 质量报告增强

---

## 13. 结论

本项目建议采用“两阶段建设”策略：

- V1 先建设发布治理骨架，证明平台具备 LLM 应用的版本管理、灰度分流、链路追踪、基础观测、规则回滚和人工扩量能力
- V2 再建设智能评测能力，提升实验判断质量和发布建议可信度

该路径的优点是：

- 范围清晰，便于落地
- 能快速形成可演示闭环
- 更符合企业真实发布控制流程
- 给后续评测智能化保留稳定扩展面

从架构角度看，V1 已足以验证该平台作为 LLM 发布治理控制层的可行性；V2 则决定该平台未来能否从“可控”进一步升级为“可判断”。
