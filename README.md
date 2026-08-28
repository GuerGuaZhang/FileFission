# FileFission

> 文件核裂变工具 + 文本分割器 - 一个简单实用的 Windows 桌面工具

## ✨ 特性

- **文件名提取**：批量提取文件名，按字符数分组输出
- **文本分割器**：按分割线切分文本，左/右键分别保存到不同目录
- **经典界面**：Windows 实用工具风格，标签栏切换功能
- **实时反馈**：底部状态栏显示操作结果，无弹窗干扰
- **单文件打包**：生成独立 EXE 文件，无需安装即可运行

## 🚀 快速开始

### 前置条件

- Python 3.7+
- tkinter（Python 默认安装）

### 安装 / 使用

**直接运行：**
```bash
python FileFission.py
```

**打包为 EXE：**
```bash
# 安装 PyInstaller
pip install pyinstaller

# 打包
pyinstaller FileFission.spec
```

打包后的文件位于 `dist/` 目录。

### 功能说明

**文件名提取：**
1. 选择包含文件名的输入文件（每行一个文件名）
2. 选择输出目录
3. 设置是否保留路径和后缀
4. 设置每组字符数（0 表示不分组）
5. 点击"开始处理"

**文本分割器：**
1. 选择源文本文件
2. 选择两个输出文件夹（A 和 B）
3. 点击"开始处理"进入分割界面
4. 左键点击分割线保存到 A，右键保存到 B

## 📁 项目结构

```
FileFission/
├── FileFission.py          # 主程序
├── FileFission.spec        # PyInstaller 配置
├── favicon.ico             # 应用图标
├── FFF.png                 # 项目 Logo
├── .gitignore              # Git 忽略规则
├── README.md               # 项目说明
├── TODO.md                 # 待办事项
├── CONTRIBUTING.md         # 贡献指南
└── dist/
    └── FileFission.exe     # 打包后的可执行文件
```

## ❓ 常见问题

**Q: 为什么选择 tkinter？**
A: tkinter 是 Python 标准库，无需额外安装，适合创建简单的桌面工具。

**Q: 如何自定义图标？**
A: 替换 `favicon.ico` 文件，然后重新运行 `pyinstaller FileFission.spec`。

**Q: 支持哪些操作系统？**
A: 目前主要支持 Windows，理论上支持所有有 tkinter 的系统。

## 📄 许可

MIT License