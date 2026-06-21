# 单机游戏存档管理器

一个基于 PyQt6 的桌面工具，用于管理本地单机游戏的存档文件。支持扫描、预览、备份、还原，以及**存档对比**。

## 功能特性

- 🏷️ **存档扫描**：手动添加目录路径，自动扫描常见 RPG 游戏的 save 目录
- 📋 **存档列表**：显示游戏名、最后修改时间、文件大小；支持搜索过滤和多种排序
- 🔍 **内容预览**：自动解析 JSON / INI 存档，提取角色名、等级、章节、游玩时长等字段
- 🆚 **存档对比**：选中两个条目（或当前槽位 + 备份）并排对比字段差异高亮；解析失败时走文本行级 diff
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
│   │   ├── backup_manager.py # 备份 / 还原管理
│   │   └── compare.py       # 存档对比（字段 diff + 文本行级 diff）
│   ├── parsers/             # 存档解析器（含插件基类）
│   │   ├── base_parser.py   # 自定义解析器基类
│   │   ├── json_parser.py   # 通用 JSON 解析器
│   │   ├── ini_parser.py    # 通用 INI 解析器
│   │   └── registry.py      # 解析器注册表与插件加载
│   └── ui/                  # PyQt6 界面
│       ├── main_window.py   # 主窗口（QStackedWidget 切换预览/对比）
│       ├── save_list.py     # 左侧存档列表（Ctrl 多选 + 对比按钮）
│       ├── preview_panel.py # 中间预览面板（单选普通视图）
│       ├── compare_panel.py # 对比主面板（Tab 切换字段/文本 Diff）
│       ├── field_compare_panel.py # 字段对比表格（差异高亮）
│       ├── text_diff_panel.py     # 文本行级 Diff 表格
│       └── action_panel.py  # 右侧操作面板（备份对比按钮）
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

---

## 存档对比

支持两种进入对比视图的方式。对比时中间面板会从「单选预览」切换为「对比模式」，可通过顶部「← 返回预览」按钮切回。

### 方式一：列表多选对比（两个当前存档槽位）

适合对比同一游戏的两个不同存档槽位（例如 Slot1 vs Slot2）。

**操作步骤**：
1. 在左侧存档列表中**先点击第一个存档**（高亮选中）
2. **按住键盘 `Ctrl` 键不放**，再点击第二个存档（此时两个条目都会高亮，按钮文字变为「对比选中 (2)」）
3. 点击列表下方的「**对比选中 (N)**」按钮 → 中间切为对比视图

> 提示：一次只能对比两个。如果选中超过两个，按钮会提示数量超限。

### 方式二：当前存档 vs 历史备份（推荐还原前确认）

适合对比「当前存档」与「某一次历史备份」之间的差异，确认内容无误后再还原。

**操作步骤**：
1. 在左侧列表点击选中某个存档（进入普通预览模式）
2. 右侧「备份历史」列表中点击你想要对比的备份条目（高亮选中）
3. 点击备份列表下方的「**🔍 与当前对比**」按钮 → 中间切为对比视图

### 对比视图说明

进入对比视图后，中间面板分为两个 Tab：

| Tab | 说明 |
|-----|------|
| **字段对比**（默认） | 三列表格：`字段名 / 存档 A / 存档 B`。<br>• 前 4 行为标准字段：角色名、等级、章节/进度、游玩时长<br>• 后续行是插件返回的 `fields` 字典所有键（按字母排序）<br>• **有差异的行以浅红底(`#ffebee`) + 深红字(`#c62828`) + 加粗 高亮显示**<br>• 表头上方显示差异统计（例如「共 3 个字段有差异（总 9 个字段）」） |
| **文本 Diff** | 四列表格：`行号A / 行号B / 变更 / 内容`。<br>• 基于 `difflib.SequenceMatcher` 行级算法<br>• `+` 绿底绿字（新增行）、`-` 红底红字（删除行）、`~` 黄底橙字（替换行）<br>• 使用 Consolas 等宽字体展示内容 |

对比视图顶部点击「**← 返回预览**」按钮即可切回单选普通预览模式；在左侧列表点选单个存档也会自动切回。

> **兜底策略**：插件钩子解析不了的文件（例如自定义二进制格式或加密存档）在「字段对比」Tab 不会有标准字段，但仍可切换到「文本 Diff」Tab 查看原始文本的行级变化，至少能看出哪几行发生了改变。

---

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
        # 自定义字段会自动出现在字段对比 Tab 的后续行
        result.fields["HP"] = "9999"
        result.fields["MP"] = "800"
        result.fields["金钱"] = "1234567"
        return result
```

### API 参考

`ParsedSaveData` 可设置的字段：

| 字段 | 类型 | 说明 |
|------|------|------|
| `raw_text` | `str` | 原始文本，用于下方预览区显示和「文本 Diff」Tab 的行级计算 |
| `fields` | `Dict[str, Any]` | **额外的键值对，会自动参与存档对比**（详见下方规则） |
| `character_name` | `Optional[str]` | 角色名（标准字段，字段对比 Tab 第 1 行） |
| `level` | `Optional[str]` | 等级（标准字段，第 2 行） |
| `chapter` | `Optional[str]` | 章节 / 进度（标准字段，第 3 行） |
| `playtime` | `Optional[str]` | 游玩时长（标准字段，第 4 行） |
| `preview_lines` | `List[str]` | 只读属性，返回 `raw_text` 前 20 行 |

**插件返回的字段如何参与对比**（重点）：

1. **四个标准属性**（`character_name` / `level` / `chapter` / `playtime`）会作为固定的前 4 行出现在「字段对比」Tab 中；
2. **`fields` 字典中的所有键**（会自动排除与标准字段重复的别名，如 `player_name`/`character_level` 等）**按字母顺序追加**到表格的后续行；
3. 任意一个字段的 A/B 值不同，该行即被**标记为差异（红底红字加粗高亮）**；
4. `raw_text` 同时会用于「文本 Diff」Tab 的行级差异计算（基于 Python 标准库 `difflib.SequenceMatcher` 算法）；
5. 插件解析失败 / 未提供 `character_name` 等标准字段时这些行显示为 `-`，但 `fields` 自定义行和 `raw_text` 文本 Diff 照常工作。

基类 `BaseParser` 还提供了辅助方法 `extract_common_fields(dict)`，可从嵌套字典中自动搜索常见的通用字段名（中英文都支持，例如 `CharacterName` / `character_name` / `角色名` 都能正确匹配到 `character_name`）。

更多示例见 `plugins/example_parser.py`。

## 数据存储位置

- 数据库：`./data/save_manager.db`（SQLite）
- 备份文件：`./backups/{游戏名}_{时间戳}/`
- 插件目录：`./plugins/`

如需迁移，整个项目目录打包带走即可。
