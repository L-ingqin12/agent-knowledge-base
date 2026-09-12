# /test — 测试生成快捷命令

## 用法

```
/test <文件路径>                    # 为指定文件生成测试
/test <文件路径> --type=<类型>      # 指定测试类型
/test --coverage                    # 分析覆盖缺口并生成补充测试
```

## 测试类型

- `unit` — 单元测试
- `integration` — 集成测试
- `e2e` — 端到端测试

## 示例

```
👤 /test src/utils/parser.js

🧠 委托 test-writer 自动检测 Jest → 生成 parser.test.js
🧪 生成 12 个测试用例: 8 单元 + 4 集成
→ 测试就绪，npm test 可运行
```
