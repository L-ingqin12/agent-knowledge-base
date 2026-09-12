# /doc — 文档生成快捷命令

## 用法

```
/doc <文件路径>                    # 为指定代码生成文档
/doc --api                         # 生成 API 文档
/doc --readme                      # 更新 README
/doc --changelog                   # 生成变更日志
```

## 示例

```
👤 /doc --api

📝 委托 doc-writer 扫描 src/api/ 目录 → 生成 API 文档
→ 文档包含: 端点列表、参数说明、返回格式、错误码
→ 输出 docs/api.md
```
