# LLM Canary Harness
<img width="2864" height="1724" alt="855e0cfe82f50a1d9e9ad1c16db92c56" src="https://github.com/user-attachments/assets/0a3f27d9-bef9-4032-8803-5af546cce76b" />

## 项目简介

LLM Canary Harness 是一个面向大模型应用的灰度发布与自动回滚平台，核心目标是在 Prompt、Model、RAG Pipeline 高频迭代的场景下，为 AI 应用提供一层独立的发布治理控制层。

在很多真实业务中，大模型应用的变化往往不是传统代码逻辑变更，而是 Prompt 调整、模型切换、参数变更、检索策略优化或输出格式修改。若这些变化直接全量上线，容易带来回答质量波动、延迟上升、调用成本失控、线上异常难追踪等问题。  
本项目希望解决的正是这一类 **“LLM 应用如何安全上线”** 的工程化难题。

项目借鉴传统互联网中的 Canary Release 思路，将其迁移到大模型应用场景中，通过版本管理、灰度实验、稳定分流、请求级 Trace、指标观测、风险规则判断、自动回滚和人工审批扩量等能力，帮助团队在不影响全量用户的前提下，对新版本进行小流量验证、异常止损和实验复盘。

---

## 项目定位

本项目不是一个聊天机器人，也不是一个单独的 RAG 系统，而是一个 **包裹在业务 AI 应用外侧的治理 Harness**。

它的作用不是替代原有模型服务，而是为现有 LLM / RAG 应用提供：

- 可管理的版本治理能力
- 可控的灰度发布能力
- 可追踪的请求链路能力
- 可观测的实验评估能力
- 可止损的风险控制能力

---

## 解决的核心问题

### 1. 版本不可管理
Prompt、Model、RAG 配置频繁变化，但很多团队缺少统一版本对象，导致线上配置难追溯、难回滚、难对比。

### 2. 新版本上线不可控
新 Prompt / 新模型直接全量上线风险较高，容易影响全量用户体验，缺少小流量验证机制。

### 3. 请求异常不可追踪
用户投诉或线上异常发生后，难以定位该请求到底命中了哪个版本、使用了哪个模型、经过了哪条调用链路。

### 4. 风险缺少自动止损
当实验版本错误率升高、延迟异常、调用不稳定时，缺少统一的护栏规则和自动回滚能力。

### 5. 发布结果难复盘
版本升级后的实验结果往往依赖人工感知，缺少统一的指标记录、决策依据和审批留痕。

---

## 核心能力

- 应用管理
- 版本管理
- 灰度实验管理
- 稳定分流（基于用户哈希、白名单、渠道规则）
- 请求级 Trace 记录
- 基础指标采集（请求量、错误率、延迟、Token、成本）
- 风险规则引擎
- 自动回滚
- 人工审批扩量
- 前端治理控制台

---

## 技术特点

- 将传统 Canary Release 思想迁移到 LLM 应用治理场景
- 将 Prompt / Model / RAG 配置统一抽象为版本对象
- 在业务系统外侧构建独立控制层，不侵入原有 RAG 项目
- 支持真实 RAG 服务接入，形成从版本发布到实验决策的闭环
- 为后续扩展 Eval Harness、LLM-as-Judge、智能实验报告保留能力边界

---

## 项目价值

LLM Canary Harness 的价值，不在于“再做一个 AI 应用”，而在于补足企业 AI 落地过程中最容易被忽视、但极其关键的一层能力：

> **让大模型应用从 Demo 式迭代，走向可控、可观测、可止损、可复盘的工程化发布流程。**

它帮助团队把 AI 版本迭代从“直接改配置上线”转变为“版本创建 → 灰度实验 → 指标观测 → 风险判断 → 回滚/扩量 → 实验复盘”的规范治理流程，从而显著提升企业 AI 应用上线的安全性与可运营性。
## 项目效果图
<img width="3356" height="1744" alt="66312d7b5be5aa5ec6282a4bb6fdc5d1" src="https://github.com/user-attachments/assets/19fd8623-2f61-4e9d-9abc-93254d691b26" />
<img width="3354" height="1834" alt="100447d5f2d5c3a176b4b4208962577c" src="https://github.com/user-attachments/assets/29193303-2e8e-49e9-88ff-6b56a6dbbe6b" />
<img width="3314" height="1896" alt="e2cdb14db0b7e129393b1c5eec5b937f" src="https://github.com/user-attachments/assets/c14790ae-ef17-4c91-ba29-520cd6f89d47" />
<img width="3334" height="1884" alt="e8c09d738356486e199580e48177ef6b" src="https://github.com/user-attachments/assets/19df0938-8550-4289-bdf6-80902c56c834" />
<img width="3356" height="1830" alt="cbd0959238a07e83f2d6a594251e3f13" src="https://github.com/user-attachments/assets/b20c173d-eb4e-4854-828b-27d2e988c54b" />
<img width="3350" height="1764" alt="ef7f4a8a3ae887810c695a947e0f6509" src="https://github.com/user-attachments/assets/c72cfc9c-0ac0-4fd0-b803-e573c68a849c" />




