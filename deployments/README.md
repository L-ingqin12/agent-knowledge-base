# 部署管控框架

每次生产环境改动必须满足四个条件，缺一不可：

## 强制规则

| # | 规则 | 含义 |
|---|------|------|
| 1 | **记录可追溯** | 改动前 git commit，描述 What/Why/How |
| 2 | **部署前验证** | deploy.sh 含预检步骤，验证通过才执行 |
| 3 | **逃生机制** | rollback.sh 可一键恢复到部署前状态 |
| 4 | **日志可审计** | 每次部署/逃生写入 deployment-log.md |

## 目录结构

```
deployments/
  ├── README.md              ← 本文件
  ├── deployment-log.md      ← 部署/逃生审计日志
  ├── diagnostic-relay/      ← 诊断中继 (relay.js)
  │   ├── deploy.sh          ← 部署 + 预检 + E2E
  │   └── rollback.sh        ← 逃生回滚
  └── proxy-timeout-fix/     ← (待实施) 代理超时修复
      ├── deploy.sh
      └── rollback.sh
```

## 部署流程

```
git commit (记录) → deploy.sh (预检→部署→E2E) → deployment-log.md (审计)
                                                        │
                                              失败? → rollback.sh (逃生)
```

## 当前部署状态

见 `deployment-log.md`
