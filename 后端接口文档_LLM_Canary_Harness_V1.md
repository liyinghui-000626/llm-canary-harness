# LLM Prompt/Model Canary Release Harness

## V1 后端接口文档

文档版本：V1.0  
文档日期：2026-05-02  
适用范围：V1 MVP  
面向对象：后端开发 / 联调工程师 / 测试工程师

---

## 1. 文档说明

本文档基于 V1 版本范围编写，覆盖以下功能模块：

- 应用管理
- 版本管理
- 灰度实验管理
- 请求网关调用
- 请求 Trace 查询
- 指标查询
- 风险决策查询
- 自动回滚
- 人工审批扩量

V1 目标是打通发布治理最小闭环，因此本文档重点覆盖：

- 输入参数
- 输出结构
- 预期结果
- 状态码约定
- 关键校验规则

---

## 2. 通用约定

### 2.1 Base URL

```text
/api/v1
```

### 2.2 请求头

```http
Content-Type: application/json
X-Request-Id: 可选，若未传则由系统生成
X-Operator: 可选，管理类操作建议透传操作人
```

### 2.3 通用响应格式

#### 成功响应

```json
{
  "code": 0,
  "message": "success",
  "data": {}
}
```

#### 失败响应

```json
{
  "code": 40001,
  "message": "invalid parameter",
  "data": null
}
```

### 2.4 通用状态码约定

| HTTP 状态码 | 含义 | 说明 |
|---|---|---|
| 200 | 成功 | 查询成功、操作成功 |
| 201 | 创建成功 | 创建资源成功 |
| 400 | 参数错误 | 缺字段、格式不合法、业务校验失败 |
| 404 | 资源不存在 | 应用、版本、实验、请求不存在 |
| 409 | 冲突 | 状态冲突、重复创建、已有运行中实验 |
| 500 | 服务异常 | 系统内部异常 |

### 2.5 通用字段说明

| 字段 | 类型 | 说明 |
|---|---|---|
| app_id | string | 应用唯一标识 |
| version_id | string | 版本唯一标识 |
| experiment_id | string | 实验唯一标识 |
| request_id | string | 请求唯一标识 |
| trace_id | string | 请求链路追踪 ID |
| operator | string | 操作人 |

---

## 3. 应用管理接口

## 3.1 创建应用

### 接口信息

- 方法：`POST`
- 路径：`/apps`

### 输入参数

```json
{
  "app_name": "AI Customer Support Bot",
  "app_type": "RAG",
  "description": "用于售后问答的智能客服应用",
  "owner": "zhangsan",
  "business_scene": "customer_support"
}
```

### 字段说明

| 字段 | 是否必填 | 类型 | 说明 |
|---|---|---|---|
| app_name | 是 | string | 应用名称，需唯一 |
| app_type | 是 | string | 应用类型，如 Chatbot / RAG / Agent |
| description | 否 | string | 应用描述 |
| owner | 是 | string | 负责人 |
| business_scene | 否 | string | 业务场景标识 |

### 输出参数

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "app_id": "app_001",
    "app_name": "AI Customer Support Bot",
    "app_type": "RAG",
    "description": "用于售后问答的智能客服应用",
    "owner": "zhangsan",
    "business_scene": "customer_support",
    "stable_version_id": null,
    "status": "active",
    "created_at": "2026-05-02T10:00:00Z"
  }
}
```

### 预期结果

- 成功创建应用记录
- 初始 `stable_version_id` 为空
- 初始状态为 `active`

### 失败场景

- `app_name` 已存在，返回 `409`
- 必填字段缺失，返回 `400`

---

## 3.2 查询应用列表

### 接口信息

- 方法：`GET`
- 路径：`/apps`

### Query 参数

| 参数 | 是否必填 | 类型 | 说明 |
|---|---|---|---|
| owner | 否 | string | 按负责人筛选 |
| app_type | 否 | string | 按应用类型筛选 |
| status | 否 | string | 按状态筛选 |
| page | 否 | int | 页码，默认 1 |
| page_size | 否 | int | 每页条数，默认 20 |

### 输出参数

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "total": 2,
    "page": 1,
    "page_size": 20,
    "items": [
      {
        "app_id": "app_001",
        "app_name": "AI Customer Support Bot",
        "app_type": "RAG",
        "owner": "zhangsan",
        "stable_version_id": "ver_001",
        "running_experiment_id": "exp_003",
        "status": "active",
        "created_at": "2026-05-02T10:00:00Z"
      }
    ]
  }
}
```

### 预期结果

- 返回分页后的应用列表
- 每个应用带出当前稳定版本和运行中实验

---

## 3.3 查询应用详情

### 接口信息

- 方法：`GET`
- 路径：`/apps/{app_id}`

### 路径参数

| 参数 | 类型 | 说明 |
|---|---|---|
| app_id | string | 应用 ID |

### 输出参数

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "app_id": "app_001",
    "app_name": "AI Customer Support Bot",
    "app_type": "RAG",
    "description": "用于售后问答的智能客服应用",
    "owner": "zhangsan",
    "business_scene": "customer_support",
    "stable_version_id": "ver_001",
    "status": "active",
    "created_at": "2026-05-02T10:00:00Z",
    "updated_at": "2026-05-02T12:00:00Z"
  }
}
```

### 预期结果

- 返回指定应用详情
- 若 `app_id` 不存在，返回 `404`

---

## 4. 版本管理接口

## 4.1 创建版本

### 接口信息

- 方法：`POST`
- 路径：`/apps/{app_id}/versions`

### 输入参数

```json
{
  "version_name": "prompt_v2_model_14b",
  "base_version_id": "ver_001",
  "prompt_template": "你是一个专业客服助手，请基于知识库回答问题。",
  "model_name": "Qwen2.5-14B-Instruct",
  "endpoint_url": "http://localhost:8000/v1/chat/completions",
  "temperature": 0.2,
  "top_p": 0.8,
  "max_tokens": 1024,
  "rag_enabled": true,
  "rag_config": {
    "vector_db": "Qdrant",
    "top_k": 5,
    "reranker_enabled": true,
    "reranker_model": "bge-reranker-large"
  },
  "output_schema": {
    "type": "markdown"
  },
  "created_by": "zhangsan"
}
```

### 字段说明

| 字段 | 是否必填 | 类型 | 说明 |
|---|---|---|---|
| version_name | 是 | string | 版本名称，应用内唯一 |
| base_version_id | 否 | string | 基于哪个版本复制 |
| prompt_template | 是 | string | Prompt 模板 |
| model_name | 是 | string | 模型名称 |
| endpoint_url | 是 | string | 模型服务地址 |
| temperature | 否 | float | 采样参数 |
| top_p | 否 | float | 采样参数 |
| max_tokens | 否 | int | 最大输出长度 |
| rag_enabled | 是 | bool | 是否开启 RAG |
| rag_config | 否 | object | RAG 配置 |
| output_schema | 否 | object | 输出格式约束 |
| created_by | 是 | string | 创建人 |

### 输出参数

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "version_id": "ver_002",
    "app_id": "app_001",
    "version_name": "prompt_v2_model_14b",
    "base_version_id": "ver_001",
    "model_name": "Qwen2.5-14B-Instruct",
    "status": "draft",
    "created_by": "zhangsan",
    "created_at": "2026-05-02T12:10:00Z"
  }
}
```

### 预期结果

- 成功创建版本对象
- 默认状态为 `draft`
- 不影响现网稳定版本

### 失败场景

- 应用不存在，返回 `404`
- `version_name` 重复，返回 `409`
- 模型地址为空或格式不合法，返回 `400`

---

## 4.2 查询版本列表

### 接口信息

- 方法：`GET`
- 路径：`/apps/{app_id}/versions`

### Query 参数

| 参数 | 是否必填 | 类型 | 说明 |
|---|---|---|---|
| status | 否 | string | 按版本状态筛选 |
| page | 否 | int | 页码 |
| page_size | 否 | int | 每页条数 |

### 输出参数

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "total": 2,
    "items": [
      {
        "version_id": "ver_001",
        "version_name": "prompt_v1_model_7b",
        "model_name": "Qwen2.5-7B-Instruct",
        "status": "stable",
        "created_at": "2026-05-02T10:30:00Z"
      },
      {
        "version_id": "ver_002",
        "version_name": "prompt_v2_model_14b",
        "model_name": "Qwen2.5-14B-Instruct",
        "status": "draft",
        "created_at": "2026-05-02T12:10:00Z"
      }
    ]
  }
}
```

### 预期结果

- 返回应用下所有版本
- 支持按状态筛选

---

## 4.3 查询版本详情

### 接口信息

- 方法：`GET`
- 路径：`/versions/{version_id}`

### 输出参数

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "version_id": "ver_002",
    "app_id": "app_001",
    "version_name": "prompt_v2_model_14b",
    "base_version_id": "ver_001",
    "prompt_template": "你是一个专业客服助手，请基于知识库回答问题。",
    "model_name": "Qwen2.5-14B-Instruct",
    "endpoint_url": "http://localhost:8000/v1/chat/completions",
    "temperature": 0.2,
    "top_p": 0.8,
    "max_tokens": 1024,
    "rag_enabled": true,
    "rag_config": {
      "vector_db": "Qdrant",
      "top_k": 5,
      "reranker_enabled": true,
      "reranker_model": "bge-reranker-large"
    },
    "output_schema": {
      "type": "markdown"
    },
    "status": "draft",
    "created_by": "zhangsan",
    "created_at": "2026-05-02T12:10:00Z",
    "updated_at": "2026-05-02T12:10:00Z"
  }
}
```

### 预期结果

- 返回完整版本配置
- 用于实验配置前校验

---

## 4.4 版本对比

### 接口信息

- 方法：`GET`
- 路径：`/versions/{version_id}/diff/{target_version_id}`

### 输出参数

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "source_version_id": "ver_001",
    "target_version_id": "ver_002",
    "diff_items": [
      {
        "field": "model_name",
        "source_value": "Qwen2.5-7B-Instruct",
        "target_value": "Qwen2.5-14B-Instruct"
      },
      {
        "field": "temperature",
        "source_value": 0.7,
        "target_value": 0.2
      },
      {
        "field": "rag_config.top_k",
        "source_value": 3,
        "target_value": 5
      }
    ]
  }
}
```

### 预期结果

- 返回两个版本的配置差异
- 用于人工确认变更内容

---

## 4.5 设置稳定版本

### 接口信息

- 方法：`POST`
- 路径：`/apps/{app_id}/stable-version`

### 输入参数

```json
{
  "version_id": "ver_001",
  "operator": "zhangsan"
}
```

### 输出参数

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "app_id": "app_001",
    "stable_version_id": "ver_001",
    "updated_at": "2026-05-02T12:20:00Z"
  }
}
```

### 预期结果

- 将指定版本标记为稳定版本
- 仅允许无运行中实验时执行

### 失败场景

- 版本不属于该应用，返回 `400`
- 存在运行中实验，返回 `409`

---

## 5. 灰度实验管理接口

## 5.1 创建实验

### 接口信息

- 方法：`POST`
- 路径：`/experiments`

### 输入参数

```json
{
  "app_id": "app_001",
  "experiment_name": "prompt_v2_canary_test",
  "control_version_id": "ver_001",
  "treatment_version_id": "ver_002",
  "traffic_control": 90,
  "traffic_treatment": 10,
  "routing_rules": {
    "hash_key": "user_id",
    "whitelist_user_ids": ["user_internal_001"],
    "channels": []
  },
  "guardrails": {
    "max_error_rate": 0.05,
    "max_latency_ratio": 1.5,
    "min_sample_size": 1000
  },
  "auto_rollback": true,
  "start_time": "2026-05-03T10:00:00Z",
  "end_time": "2026-05-06T10:00:00Z",
  "created_by": "zhangsan"
}
```

### 字段说明

| 字段 | 是否必填 | 类型 | 说明 |
|---|---|---|---|
| app_id | 是 | string | 应用 ID |
| experiment_name | 是 | string | 实验名称 |
| control_version_id | 是 | string | 对照版本 |
| treatment_version_id | 是 | string | 实验版本 |
| traffic_control | 是 | int | 对照组流量百分比 |
| traffic_treatment | 是 | int | 实验组流量百分比 |
| routing_rules | 是 | object | 路由规则 |
| guardrails | 是 | object | 护栏配置 |
| auto_rollback | 是 | bool | 是否允许自动回滚 |
| start_time | 否 | string | 开始时间 |
| end_time | 否 | string | 结束时间 |
| created_by | 是 | string | 创建人 |

### 输出参数

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "experiment_id": "exp_003",
    "app_id": "app_001",
    "experiment_name": "prompt_v2_canary_test",
    "control_version_id": "ver_001",
    "treatment_version_id": "ver_002",
    "traffic_control": 90,
    "traffic_treatment": 10,
    "status": "created",
    "auto_rollback": true,
    "created_at": "2026-05-02T13:00:00Z"
  }
}
```

### 预期结果

- 创建实验配置成功
- 初始状态为 `created`
- 不自动启动实验

### 失败场景

- 同一应用已有运行中实验，返回 `409`
- 流量总和不等于 100，返回 `400`
- 对照版本与实验版本相同，返回 `400`

---

## 5.2 启动实验

### 接口信息

- 方法：`POST`
- 路径：`/experiments/{experiment_id}/start`

### 输入参数

```json
{
  "operator": "zhangsan"
}
```

### 输出参数

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "experiment_id": "exp_003",
    "status": "running",
    "started_at": "2026-05-03T10:00:00Z"
  }
}
```

### 预期结果

- 实验进入 `running`
- 后续请求开始按实验规则分流

### 失败场景

- 实验状态不是 `created`，返回 `409`
- 对照版本不是稳定版本，返回 `400`

---

## 5.3 停止实验

### 接口信息

- 方法：`POST`
- 路径：`/experiments/{experiment_id}/stop`

### 输入参数

```json
{
  "operator": "zhangsan",
  "reason": "manual stop"
}
```

### 输出参数

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "experiment_id": "exp_003",
    "status": "stopped",
    "stopped_at": "2026-05-03T12:30:00Z"
  }
}
```

### 预期结果

- 停止实验
- 后续流量恢复至稳定版本

---

## 5.4 查询实验列表

### 接口信息

- 方法：`GET`
- 路径：`/experiments`

### Query 参数

| 参数 | 是否必填 | 类型 | 说明 |
|---|---|---|---|
| app_id | 否 | string | 应用 ID |
| status | 否 | string | 实验状态 |
| page | 否 | int | 页码 |
| page_size | 否 | int | 每页条数 |

### 输出参数

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "total": 1,
    "items": [
      {
        "experiment_id": "exp_003",
        "app_id": "app_001",
        "experiment_name": "prompt_v2_canary_test",
        "control_version_id": "ver_001",
        "treatment_version_id": "ver_002",
        "traffic_control": 90,
        "traffic_treatment": 10,
        "status": "running",
        "auto_rollback": true,
        "created_at": "2026-05-02T13:00:00Z"
      }
    ]
  }
}
```

### 预期结果

- 返回实验列表
- 支持按应用和状态筛选

---

## 5.5 查询实验详情

### 接口信息

- 方法：`GET`
- 路径：`/experiments/{experiment_id}`

### 输出参数

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "experiment_id": "exp_003",
    "app_id": "app_001",
    "experiment_name": "prompt_v2_canary_test",
    "control_version_id": "ver_001",
    "treatment_version_id": "ver_002",
    "traffic_control": 90,
    "traffic_treatment": 10,
    "routing_rules": {
      "hash_key": "user_id",
      "whitelist_user_ids": ["user_internal_001"],
      "channels": []
    },
    "guardrails": {
      "max_error_rate": 0.05,
      "max_latency_ratio": 1.5,
      "min_sample_size": 1000
    },
    "status": "running",
    "auto_rollback": true,
    "start_time": "2026-05-03T10:00:00Z",
    "end_time": "2026-05-06T10:00:00Z",
    "created_by": "zhangsan"
  }
}
```

### 预期结果

- 返回实验完整配置与状态

---

## 6. 请求网关接口

## 6.1 网关调用

### 接口信息

- 方法：`POST`
- 路径：`/gateway/invoke`

### 输入参数

```json
{
  "app_id": "app_001",
  "user_id": "user_123",
  "session_id": "sess_789",
  "query": "我的订单什么时候发货？",
  "metadata": {
    "channel": "web",
    "region": "CN",
    "user_level": "normal"
  }
}
```

### 字段说明

| 字段 | 是否必填 | 类型 | 说明 |
|---|---|---|---|
| app_id | 是 | string | 应用 ID |
| user_id | 是 | string | 用户 ID，用于稳定分流 |
| session_id | 否 | string | 会话 ID |
| query | 是 | string | 用户输入 |
| metadata | 否 | object | 扩展路由字段 |

### 输出参数

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "request_id": "req_001",
    "trace_id": "trace_abc123",
    "experiment_id": "exp_003",
    "version_id": "ver_002",
    "routing_reason": "hash_bucket_hit_treatment",
    "answer": "根据当前订单信息，您的订单预计将在 24 小时内发货。",
    "model_name": "Qwen2.5-14B-Instruct",
    "latency_ms": 1320,
    "input_tokens": 820,
    "output_tokens": 236,
    "total_tokens": 1056,
    "cost": 0.0021,
    "status": "success"
  }
}
```

### 预期结果

- 请求进入平台统一网关
- 若存在运行中实验，则按规则命中版本
- 若不存在运行中实验，则走稳定版本
- 返回模型回答，同时完成请求日志落库

### 失败场景

- 应用不存在，返回 `404`
- 没有稳定版本可用，返回 `400`
- 模型调用失败，返回 `500`，同时 `status=error` 写入日志

---

## 6.2 网关调用预期内部行为

该接口除返回响应外，还需完成以下内部处理：

1. 查询应用配置
2. 查询运行中实验
3. 根据白名单 / 渠道 / 哈希桶命中版本
4. 加载版本配置
5. 若 `rag_enabled=true`，执行检索流程
6. 调用模型服务
7. 记录 Token、耗时、错误信息
8. 生成 `request_id` 和 `trace_id`
9. 写入 `request_logs`

---

## 7. 请求 Trace 查询接口

## 7.1 查询单次请求详情

### 接口信息

- 方法：`GET`
- 路径：`/requests/{request_id}`

### 输出参数

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "request_id": "req_001",
    "trace_id": "trace_abc123",
    "app_id": "app_001",
    "experiment_id": "exp_003",
    "version_id": "ver_002",
    "user_id": "user_123",
    "session_id": "sess_789",
    "query": "我的订单什么时候发货？",
    "answer": "根据当前订单信息，您的订单预计将在 24 小时内发货。",
    "routing_reason": "hash_bucket_hit_treatment",
    "model_name": "Qwen2.5-14B-Instruct",
    "retrieval_docs": [
      "doc_001",
      "doc_008"
    ],
    "input_tokens": 820,
    "output_tokens": 236,
    "total_tokens": 1056,
    "latency_ms": 1320,
    "cost": 0.0021,
    "status": "success",
    "error_message": null,
    "created_at": "2026-05-03T10:01:05Z"
  }
}
```

### 预期结果

- 返回该请求完整执行链路
- 支持用于问题定位和复盘

---

## 7.2 查询请求列表

### 接口信息

- 方法：`GET`
- 路径：`/requests`

### Query 参数

| 参数 | 是否必填 | 类型 | 说明 |
|---|---|---|---|
| app_id | 否 | string | 应用 ID |
| experiment_id | 否 | string | 实验 ID |
| version_id | 否 | string | 版本 ID |
| status | 否 | string | success / error |
| start_time | 否 | string | 开始时间 |
| end_time | 否 | string | 结束时间 |
| page | 否 | int | 页码 |
| page_size | 否 | int | 每页条数 |

### 输出参数

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "total": 100,
    "items": [
      {
        "request_id": "req_001",
        "trace_id": "trace_abc123",
        "experiment_id": "exp_003",
        "version_id": "ver_002",
        "routing_reason": "hash_bucket_hit_treatment",
        "latency_ms": 1320,
        "cost": 0.0021,
        "status": "success",
        "created_at": "2026-05-03T10:01:05Z"
      }
    ]
  }
}
```

### 预期结果

- 支持按实验、版本、状态、时间筛选请求记录

---

## 8. 指标查询接口

## 8.1 查询实验指标总览

### 接口信息

- 方法：`GET`
- 路径：`/experiments/{experiment_id}/metrics`

### Query 参数

| 参数 | 是否必填 | 类型 | 说明 |
|---|---|---|---|
| start_time | 否 | string | 开始时间 |
| end_time | 否 | string | 结束时间 |
| interval | 否 | string | 聚合粒度，如 1m / 5m / 1h |

### 输出参数

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "experiment_id": "exp_003",
    "control": {
      "version_id": "ver_001",
      "request_count": 900,
      "success_count": 890,
      "error_count": 10,
      "error_rate": 0.0111,
      "avg_latency_ms": 1180,
      "p95_latency_ms": 1600,
      "avg_cost": 0.0015,
      "avg_input_tokens": 700,
      "avg_output_tokens": 210
    },
    "treatment": {
      "version_id": "ver_002",
      "request_count": 100,
      "success_count": 94,
      "error_count": 6,
      "error_rate": 0.06,
      "avg_latency_ms": 2100,
      "p95_latency_ms": 2900,
      "avg_cost": 0.0031,
      "avg_input_tokens": 820,
      "avg_output_tokens": 236
    },
    "generated_at": "2026-05-03T11:00:00Z"
  }
}
```

### 预期结果

- 返回实验对照组和实验组核心运行指标
- 指标来源统一基于 `request_logs` 聚合

---

## 8.2 查询实验时序指标

### 接口信息

- 方法：`GET`
- 路径：`/experiments/{experiment_id}/metrics/timeseries`

### Query 参数

| 参数 | 是否必填 | 类型 | 说明 |
|---|---|---|---|
| metric | 是 | string | 指标名，如 `error_rate` / `avg_latency_ms` |
| interval | 是 | string | 聚合粒度，如 `5m` |
| start_time | 是 | string | 开始时间 |
| end_time | 是 | string | 结束时间 |

### 输出参数

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "metric": "error_rate",
    "interval": "5m",
    "control": [
      {
        "timestamp": "2026-05-03T10:00:00Z",
        "value": 0.01
      }
    ],
    "treatment": [
      {
        "timestamp": "2026-05-03T10:00:00Z",
        "value": 0.06
      }
    ]
  }
}
```

### 预期结果

- 用于 Dashboard 绘制趋势图

---

## 9. 风险决策接口

## 9.1 查询当前决策结果

### 接口信息

- 方法：`GET`
- 路径：`/experiments/{experiment_id}/decision`

### 输出参数

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "experiment_id": "exp_003",
    "decision_type": "rollback",
    "risk_level": "high",
    "triggered_rules": [
      {
        "rule_name": "max_error_rate",
        "reason": "treatment.error_rate=0.06 > 0.05"
      },
      {
        "rule_name": "max_latency_ratio",
        "reason": "treatment.avg_latency_ms=2100 > control.avg_latency_ms*1.5"
      }
    ],
    "recommended_next_split": null,
    "requires_manual_approval": false,
    "evaluated_at": "2026-05-03T11:00:00Z"
  }
}
```

### 预期结果

- 返回当前实验的最近一次规则判断结果
- 可为前端展示“继续观察 / 建议扩量 / 自动回滚”

---

## 9.2 触发手动重算决策

### 接口信息

- 方法：`POST`
- 路径：`/experiments/{experiment_id}/decision/recompute`

### 输入参数

```json
{
  "operator": "zhangsan"
}
```

### 输出参数

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "experiment_id": "exp_003",
    "decision_type": "keep_observing",
    "risk_level": "medium",
    "triggered_rules": [
      {
        "rule_name": "sample_size_not_enough",
        "reason": "treatment.request_count=120 < min_sample_size=1000"
      }
    ],
    "recommended_next_split": null,
    "requires_manual_approval": false,
    "evaluated_at": "2026-05-03T10:20:00Z"
  }
}
```

### 预期结果

- 重新读取最新指标并计算实验结论
- 不直接执行扩量或回滚动作，仅返回判断结果

---

## 10. 回滚接口

## 10.1 手动触发回滚

### 接口信息

- 方法：`POST`
- 路径：`/experiments/{experiment_id}/rollback`

### 输入参数

```json
{
  "operator": "zhangsan",
  "reason": "manual rollback due to latency spike"
}
```

### 输出参数

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "rollback_id": "rb_001",
    "experiment_id": "exp_003",
    "from_version_id": "ver_002",
    "to_version_id": "ver_001",
    "status": "success",
    "reason": "manual rollback due to latency spike",
    "rollback_at": "2026-05-03T11:05:00Z"
  }
}
```

### 预期结果

- 当前实验立即停止
- 实验版本流量切回 `0%`
- 稳定版本恢复 `100%`
- 写入 `rollback_logs`

### 失败场景

- 实验不处于运行状态，返回 `409`

---

## 10.2 查询回滚日志

### 接口信息

- 方法：`GET`
- 路径：`/experiments/{experiment_id}/rollback-logs`

### 输出参数

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "items": [
      {
        "rollback_id": "rb_001",
        "experiment_id": "exp_003",
        "from_version_id": "ver_002",
        "to_version_id": "ver_001",
        "trigger_rule": "max_error_rate",
        "reason": "treatment.error_rate=0.06 > 0.05",
        "operator": "system",
        "status": "success",
        "created_at": "2026-05-03T11:05:00Z"
      }
    ]
  }
}
```

### 预期结果

- 返回实验相关回滚历史
- 包含自动回滚和手动回滚记录

---

## 11. 人工审批扩量接口

## 11.1 查询扩量建议

### 接口信息

- 方法：`GET`
- 路径：`/experiments/{experiment_id}/expand-recommendation`

### 输出参数

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "experiment_id": "exp_003",
    "current_split": "90/10",
    "recommended_split": "70/30",
    "decision_type": "recommend_expand",
    "risk_level": "low",
    "reasons": [
      "sample_size_ready",
      "error_rate_stable",
      "latency_within_guardrail"
    ],
    "requires_manual_approval": true,
    "generated_at": "2026-05-03T18:00:00Z"
  }
}
```

### 预期结果

- 返回当前实验是否具备扩量建议
- 若无建议，可返回 `decision_type=keep_observing`

---

## 11.2 审批扩量

### 接口信息

- 方法：`POST`
- 路径：`/experiments/{experiment_id}/approve-expand`

### 输入参数

```json
{
  "operator": "zhangsan",
  "approved": true,
  "approved_split": {
    "control": 70,
    "treatment": 30
  },
  "approval_reason": "核心指标稳定，批准扩大实验流量"
}
```

### 字段说明

| 字段 | 是否必填 | 类型 | 说明 |
|---|---|---|---|
| operator | 是 | string | 审批人 |
| approved | 是 | bool | 是否批准 |
| approved_split | 条件必填 | object | 批准后的流量比例 |
| approval_reason | 否 | string | 审批说明 |

### 输出参数

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "approval_id": "ap_001",
    "experiment_id": "exp_003",
    "old_split": {
      "control": 90,
      "treatment": 10
    },
    "new_split": {
      "control": 70,
      "treatment": 30
    },
    "approved_by": "zhangsan",
    "status": "approved",
    "approved_at": "2026-05-03T18:10:00Z"
  }
}
```

### 预期结果

- 审批通过后更新实验流量比例
- 仅在 `decision_type=recommend_expand` 时允许审批
- 必须记录审批日志

### 失败场景

- 当前没有扩量建议，返回 `409`
- 流量和不等于 100，返回 `400`
- 实验已停止或已回滚，返回 `409`

---

## 11.3 查询审批日志

### 接口信息

- 方法：`GET`
- 路径：`/experiments/{experiment_id}/approval-logs`

### 输出参数

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "items": [
      {
        "approval_id": "ap_001",
        "experiment_id": "exp_003",
        "current_split": "90/10",
        "recommended_split": "70/30",
        "approved_by": "zhangsan",
        "approval_reason": "核心指标稳定，批准扩大实验流量",
        "status": "approved",
        "created_at": "2026-05-03T18:10:00Z"
      }
    ]
  }
}
```

### 预期结果

- 返回实验下所有扩量审批记录
- 用于审计与复盘

---

## 12. 异步任务与系统行为说明

V1 除同步接口外，后端还需要具备以下异步任务能力：

### 12.1 指标聚合任务

用途：

- 定时从 `request_logs` 聚合实验指标
- 计算请求量、错误率、延迟、Token、成本

建议频率：

- 每 1 分钟执行一次

### 12.2 风险规则评估任务

用途：

- 读取最新实验指标
- 判断 `rollback / keep_observing / recommend_expand`

建议频率：

- 每 1 分钟执行一次

### 12.3 自动回滚任务

触发条件：

- 当规则评估结果为 `rollback`
- 且实验允许 `auto_rollback=true`

预期结果：

- 自动调用回滚逻辑
- 更新实验状态
- 记录回滚日志

---

## 13. V1 接口联调顺序建议

建议后端按以下顺序开发和联调：

1. 应用管理接口
2. 版本管理接口
3. 实验管理接口
4. 网关调用接口
5. 请求日志与 Trace 查询接口
6. 指标聚合查询接口
7. 风险决策接口
8. 回滚接口
9. 扩量审批接口

---

## 14. 验收口径建议

V1 接口层建议按以下标准验收：

### 14.1 版本管理

- 能创建应用
- 能创建多个版本
- 能查看版本差异
- 能设置稳定版本

### 14.2 实验与分流

- 能创建并启动实验
- 同一用户多次请求稳定命中同一版本
- 无实验时默认走稳定版本

### 14.3 可观测性

- 每次调用都能生成 `request_id` 和 `trace_id`
- 能查询单次请求完整链路
- 能聚合实验级基础指标

### 14.4 回滚与审批

- 命中硬护栏可触发回滚
- 审批通过可执行扩量
- 所有操作均可查日志

---

## 15. 后续扩展说明

V2 会在此接口体系基础上新增：

- 评测任务接口
- 评测结果查询接口
- 离线数据集管理接口
- 在线抽样评测接口
- 智能实验报告接口

V1 设计时需预留：

- `eval_results` 表
- 请求与评测结果关联字段
- 决策结果可扩展更多质量维度

