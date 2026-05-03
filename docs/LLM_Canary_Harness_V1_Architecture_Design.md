# LLM Canary Harness V1 架构设计文档

文档版本：V1.0  
编写日期：2026-05-02  
适用范围：LLM Prompt/Model Canary Release Harness 第一阶段建设

## 1. 文档目标

本文档基于当前 V1 范围，输出一套可直接进入研发实施阶段的正式架构方案，覆盖：

- 前端架构设计
- 后端架构设计
- 模块职责分工
- Milvus `Canary` 数据库设计
- 代码目录规划
- V1 研发边界与交付建议

V1 目标聚焦“发布治理最小闭环”，不引入复杂自动质量评测，只建设：

- 应用管理
- 版本管理
- 灰度实验管理
- 请求网关与稳定分流
- 请求 Trace 与基础指标
- 风险规则引擎
- 自动回滚
- 人工审批扩量

## 2. 总体建设原则

### 2.1 架构原则

1. 前后端分离，前端专注治理控制台，后端专注业务编排与执行控制。
2. V1 采用模块化单体，避免过早微服务化。
3. 在线请求链路与后台聚合任务解耦。
4. 分流逻辑统一放在平台网关，不侵入业务应用。
5. 所有关键动作可追踪、可审计、可回放。

### 2.2 V1 关键能力目标

- 可管理：应用、版本、实验都有清晰生命周期
- 可分流：请求能按稳定规则进入不同版本
- 可观测：请求、指标、路由理由都可追踪
- 可止损：硬护栏触发自动回滚
- 可审批：扩量动作必须人工确认

## 3. 总体逻辑架构

```text
前端控制台
  |
  v
Admin API
  |
  +-- 应用管理服务
  +-- 版本管理服务
  +-- 实验管理服务
  +-- 审批管理服务
  +-- Dashboard 查询服务
  |
  v
Gateway API
  |
  +-- 实验查询
  +-- 稳定分流
  +-- 版本配置加载
  +-- Prompt / RAG / Model 编排
  +-- 请求 Trace 记录
  |
  v
LLM / RAG Provider

Worker
  |
  +-- 指标聚合任务
  +-- 风险规则判断
  +-- 自动回滚任务
  +-- 扩量建议生成

数据层
  |
  +-- Milvus (Canary)
  +-- Redis
```

## 4. 前端架构设计

### 4.1 前端定位

前端是发布治理控制台，不承载模型推理逻辑，主要负责平台配置、可视化展示和人工审批。

### 4.2 前端职责

#### A. 应用管理

- 创建应用
- 查询应用列表
- 查看应用详情
- 查看应用关联版本与实验

#### B. 版本管理

- 创建版本
- 基于历史版本复制
- 查看版本详情
- 比较两个版本的配置差异
- 标记稳定版本

#### C. 灰度实验管理

- 创建实验
- 选择对照版本与实验版本
- 配置流量比例
- 配置自动回滚开关
- 启动与停止实验

#### D. 实验看板

- 当前实验状态
- 流量分布
- 风险等级
- 建议动作
- 版本指标对比

#### E. 请求 Trace

- 请求命中版本
- 路由原因
- 调用模型
- 延迟、错误、Token、成本

#### F. 审批中心

- 查看扩量建议
- 人工审批扩量
- 审批意见记录

#### G. 回滚日志

- 回滚时间
- 触发规则
- 回滚原因
- 回滚结果

### 4.3 前端推荐技术栈

- React
- TypeScript
- Ant Design
- React Router
- Zustand 或 Redux Toolkit
- ECharts

### 4.4 前端代码目录

```text
frontend/
└── src/
    ├── api/
    ├── pages/
    │   ├── apps/
    │   ├── versions/
    │   ├── experiments/
    │   ├── dashboard/
    │   ├── traces/
    │   ├── approvals/
    │   └── rollback/
    ├── components/
    │   ├── forms/
    │   ├── charts/
    │   ├── tables/
    │   └── layout/
    ├── store/
    ├── types/
    ├── utils/
    └── router/
```

### 4.5 前端模块说明

- `api/`：统一封装对 Admin API 的请求
- `pages/apps`：应用管理页面
- `pages/versions`：版本创建、查看、差异对比
- `pages/experiments`：实验配置、状态管理
- `pages/dashboard`：指标图表与风险概览
- `pages/traces`：请求明细与链路查询
- `pages/approvals`：扩量审批工作台
- `pages/rollback`：回滚日志页面

## 5. 后端架构设计

### 5.1 后端定位

后端由三类运行单元组成：

1. `admin_api`：面向前端控制台
2. `gateway_api`：面向业务请求入口
3. `worker`：异步任务执行器

### 5.2 Admin API 职责

- 应用管理
- 版本管理
- 实验管理
- 扩量审批
- Dashboard 查询
- Trace 查询
- 回滚日志查询

### 5.3 Gateway API 职责

- 接收线上业务请求
- 根据 `app_id` 查询实验
- 根据分流规则稳定命中版本
- 加载版本配置
- 编排 Prompt / RAG / Model 调用
- 返回结果
- 写入请求 Trace

### 5.4 Worker 职责

- 聚合实验指标
- 定时运行风险规则
- 触发自动回滚
- 生成扩量建议

### 5.5 后端推荐技术栈

- FastAPI
- Pydantic
- pymilvus
- Redis
- APScheduler 或 Celery
- httpx

### 5.6 后端代码目录

```text
backend/
├── apps/
│   ├── admin_api/
│   ├── gateway_api/
│   └── worker/
└── app/
    ├── api/
    │   ├── admin/
    │   └── gateway/
    ├── schemas/
    ├── domain/
    │   ├── entities/
    │   ├── enums/
    │   └── value_objects/
    ├── services/
    ├── repositories/
    │   ├── milvus/
    │   └── redis/
    ├── adapters/
    │   ├── llm/
    │   ├── rag/
    │   └── notifier/
    ├── tasks/
    ├── core/
    └── utils/
```

### 5.7 后端模块职责说明

#### `services/`

- `app_service.py`：应用增删改查
- `version_service.py`：版本配置与状态流转
- `experiment_service.py`：实验创建、启动、停止
- `routing_service.py`：稳定哈希分流、白名单、渠道分流
- `invoke_service.py`：执行链路编排
- `trace_service.py`：请求链路记录
- `metric_service.py`：基础指标聚合
- `rule_engine_service.py`：规则判断
- `rollback_service.py`：自动回滚
- `approval_service.py`：人工审批扩量

#### `repositories/milvus/`

负责对 `Canary` 数据库下 collection 做统一读写。

#### `repositories/redis/`

负责缓存以下内容：

- 当前运行实验
- 热点版本配置
- 稳定分流路由缓存

#### `adapters/llm/`

抽象多模型服务接入，支持：

- OpenAI-compatible API
- vLLM
- Qwen API

#### `adapters/rag/`

封装 RAG 调用链，为后续接向量检索或知识库服务预留扩展点。

## 6. 核心处理流程

### 6.1 V1 请求执行主链路

1. 业务系统调用 `POST /gateway/invoke`
2. 网关读取 `app_id`
3. 查询该应用是否存在运行中的实验
4. 使用 `user_id hash` 进行稳定分流
5. 加载命中版本配置
6. 拼接 Prompt，按需调用 RAG
7. 调用模型服务
8. 记录请求 Trace
9. 返回推理结果

### 6.2 V1 自动回滚链路

1. Worker 周期性聚合实验指标
2. 风险规则引擎判断是否命中硬护栏
3. 若命中，生成 `rollback` 决策
4. 停止实验并将实验流量置零
5. 恢复稳定版本流量
6. 写入回滚日志
7. 发送通知

### 6.3 V1 扩量审批链路

1. Worker 周期性生成扩量建议
2. 前端审批中心展示建议依据
3. 负责人人工审批
4. Admin API 执行流量调整
5. 记录审批日志

## 7. Milvus 数据库设计

### 7.1 数据库

- 数据库名称：`Canary`

### 7.2 Collection 规划

- `applications`
- `model_versions`
- `experiments`
- `routing_rules`
- `request_traces`
- `metric_snapshots`
- `rollback_logs`
- `approval_logs`

### 7.3 Collection 设计原则

1. V1 请求事实数据统一进入 `request_traces`
2. 聚合指标来自请求事实数据，不单独手工写口径
3. 规则、审批、回滚全部留痕
4. 预留向量字段，支持 V2 相似请求分析

## 8. 关键接口边界

### 8.1 Admin API

- `POST /api/apps`
- `GET /api/apps`
- `POST /api/apps/{app_id}/versions`
- `GET /api/apps/{app_id}/versions`
- `POST /api/experiments`
- `POST /api/experiments/{experiment_id}/start`
- `POST /api/experiments/{experiment_id}/stop`
- `POST /api/experiments/{experiment_id}/approve-expand`
- `GET /api/experiments/{experiment_id}/metrics`
- `GET /api/requests/{request_id}`
- `GET /api/rollback-logs`

### 8.2 Gateway API

- `POST /gateway/invoke`

## 9. V1 研发交付建议

### 9.1 第一批必须完成

- 目录骨架
- Milvus 建库建 collection
- 应用管理 API
- 版本管理 API
- 实验管理 API
- Gateway 路由主链路
- 请求 Trace 落库

### 9.2 第二批补齐

- 指标聚合任务
- 风险规则任务
- 自动回滚
- Dashboard 查询接口
- 审批扩量接口

### 9.3 第三批完善展示

- 前端 Dashboard
- Trace 明细页
- 回滚日志页
- 审批中心

## 10. 结论

V1 最合适的实现方式是：

- 前端建设治理控制台
- 后端建设模块化单体
- 在线请求和异步任务分离
- 使用 Milvus `Canary` 承载平台数据
- 使用 Redis 承担热点缓存与分流加速

这套设计既能快速形成可演示闭环，也为 V2 的智能评测保留了稳定扩展面。
