# 贡献指南

感谢您对 FileFission 项目的关注！

## 如何贡献

### 报告问题
- 使用 GitHub Issues 报告 bug
- 请提供详细的复现步骤
- 包含操作系统和 Python 版本信息

### 提交代码
1. Fork 项目
2. 创建功能分支：`git checkout -b feature/your-feature`
3. 提交更改：`git commit -m 'Add some feature'`
4. 推送到分支：`git push origin feature/your-feature`
5. 创建 Pull Request

### 代码规范
- 遵循 PEP 8 编码规范
- 添加必要的注释
- 确保代码可以正常运行

### 功能建议
- 在 Issues 中提出功能建议
- 说明功能的使用场景
- 提供设计思路（如果有的话）

## 开发环境

### 环境要求
- Python 3.7+
- tkinter（Python 默认安装）

### 运行项目
```bash
python FileFission.py
```

### 打包项目
```bash
pip install pyinstaller
pyinstaller FileFission.spec
```

## 项目结构

```
FileFission/
├── FileFission.py      # 主程序
├── FileFission.spec    # PyInstaller 配置
├── .gitignore          # Git 忽略规则
├── README.md           # 项目说明
├── TODO.md             # 待办事项
└── CONTRIBUTING.md     # 贡献指南
```

## 联系方式

如有任何问题，请通过 GitHub Issues 联系我们。

---

感谢您的贡献！