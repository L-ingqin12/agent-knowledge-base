# /secure — 安全审计快捷命令

## 用法

```
/secure <文件或目录路径>
/secure --full                     # 全项目安全审计
/secure --deps                     # 仅检查依赖漏洞
```

## 示例

```
👤 /secure src/api/

🛡️ 委托 security-auditor 扫描 src/api/ 所有端点
→ 发现 2 个 OWASP Top 10 漏洞 + 3 个依赖 CVE
→ 输出分级安全报告（严重/高危/中危/低危）
```
