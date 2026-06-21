# 单机游戏存档管理器

一个基于 PyQt6 的桌面工具，用于管理本地单机游戏的存档文件。支持扫描、预览、备份和还原存档。

## 功能特性

- 🏷️ **存档扫描**：手动添加目录路径，自动扫描常见 RPG 游戏的 save 目录
- 📋 **存档列表**：显示游戏名、最后修改时间、文件大小；支持搜索过滤和多种排序
- 🔍 **内容预览**：自动解析 JSON / INI 存档，提取角色名、等级、章节、游玩时长等字段
- 📦 **一键备份**：将存档复制到 `backups/` 目录，自动按时间戳命名
- ↩️ **安全还原**：还原前弹出确认框，防止误操作覆盖
- ✏️ **备注管理**：为每个存档添加自定义备注
- 🔌 **插件系统**：支持自定义游戏解析器，插件热加载
- 💾 **持久化**：所有配置、备注、备份记录保存在本地 SQLite 数据库

## 目录结构

```
.
├── main.py                  # 程序入口
├── requirements.txt         # 依赖
├── app/
│   ├── core/                # 核心逻辑
│   │   ├── models.py        # 数据模型
│   │   ├── database.py      # SQLite 数据库操作
│   │   ├── scanner.py       # 存档目录扫描器
│   │   └── backup_manager.py # 备份 / 还原管理
│   ├── parsers/             # 存档解析器（含插件基类）
│   │   ├── base_parser.py   # 自定义解析器基类
│   │   ├── json_parser.py   # 通用 JSON 解析器
│   │   ├── ini_parser.py    # 通用 INI 解析器
│   │   └── registry.py      # 解析器注册表与插件加载
│   └── ui/                  # PyQt6 界面
│       ├── main_window.py   # 主窗口
│       ├── save_list.py     # 左侧存档列表
│       ├── preview_panel.py # 中间预览面板
│       └── action_panel.py  # 右侧操作面板
├── plugins/                 # 自定义解析插件目录
│   └── example_parser.py    # 示例插件
├── data/                    # 运行时生成：SQLite 数据库
└── backups/                 # 运行时生成：备份文件存放目录
```

## 环境要求

- Python 3.9+
- Windows 10 / 11（也支持 macOS / Linux）

## 安装依赖

```bash
pip install -r requirements.txt
```

## 运行

两种方式任选其一：

**方式一：命令行启动**
```bash
python main.py
```

**方式二：Windows 双击**

创建一个 `.bat` 文件（例如 `启动.bat`）放在项目根目录，内容如下，双击即可运行：

```batch
@echo off
python main.py
pause
```

## 使用说明

1. **添加扫描路径**：点击左下角「添加扫描路径」，选择游戏存档所在文件夹（例如 `C:\Users\你\Saved Games\`）
2. **扫描存档**：点击「重新扫描」，程序会在后台线程扫描所有已添加的目录
3. **查看详情**：在左侧列表点击任意存档，中间面板会显示解析出的字段和原始内容预览
4. **备份 / 还原 / 改备注**：使用右侧面板的三个按钮操作
5. **搜索过滤**：顶部搜索框输入关键词，按名称/路径/备注实时过滤；下拉框可切换排序方式

## 添加自定义游戏解析插件

内置的 JSON / INI 解析器只能做通用字段提取。如果某个游戏的存档格式比较特殊，可以写一个自定义解析插件：

### 步骤

1. 在 `plugins/` 目录下新建一个 `.py` 文件，例如 `my_game_parser.py`
2. 继承 `app.parsers.base_parser.BaseParser` 并实现两个抽象方法
3. 保存文件，重启程序即可自动加载（无需修改其他代码）

### 最小示例

```python
import os
from app.parsers.base_parser import BaseParser
from app.core.models import ParsedSaveData

class MyRPGParser(BaseParser):
    name = "MyRPGParser"
    description = "解析《我的RPG》存档"
    file_extensions = [".rpg"]      # 匹配的后缀
    game_identifiers = ["my_rpg"]   # 可选：用于路径匹配

    def can_parse(self, file_path: str) -> bool:
        """返回 True 表示此解析器可以处理该文件"""
        ext = os.path.splitext(file_path)[1].lower()
        return ext == ".rpg"

    def parse(self, file_path: str) -> ParsedSaveData:
        """解析存档并返回结构化数据"""
        with open(file_path, "r", encoding="utf-8") as f:
            raw = f.read()

        result = ParsedSaveData(raw_text=raw)
        # 在这里写你的解析逻辑
        result.character_name = "勇者"
        result.level = "42"
        result.chapter = "第五章"
        result.playtime = "25小时30分"
        return result
```

### API 参考

`ParsedSaveData` 可设置的字段：

| 字段 | 类型 | 说明 |
|------|------|------|
| `raw_text` | `str` | 原始文本，用于下方预览区显示 |
| `fields` | `Dict[str, Any]` | 额外的键值对（预留） |
| `character_name` | `Optional[str]` | 角色名 |
| `level` | `Optional[str]` | 等级 |
| `chapter` | `Optional[str]` | 章节 / 进度 |
| `playtime` | `Optional[str]` | 游玩时长 |
| `preview_lines` | `List[str]` | 只读，返回 `raw_text` 前 20 行 |

基类 `BaseParser` 还提供了辅助方法 `extract_common_fields(dict)`，可从嵌套字典中自动搜索常见的通用字段名（中英文都支持）。

更多示例见 `plugins/example_parser.py`。

## 数据存储位置

- 数据库：`./data/save_manager.db`（SQLite）
- 备份文件：`./backups/{游戏名}_{时间戳}/`
- 插件目录：`./plugins/`

如需迁移，整个项目目录打包带走即可。
