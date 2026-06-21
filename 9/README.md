# 小工作室客户跟进管理（StudioCRM）

本地桌面版客户跟进工具，给小工作室用。纯 Python + PyQt6，数据存 SQLite，不需要服务器。

## 功能一览

- **三栏布局**：左侧客户列表（筛选/搜索/排序）、中间客户详情、右侧沟通时间线
- **客户管理**：公司、联系人、电话、跟进阶段、标签、下次提醒日期
- **时间线记录**：每次沟通摘要倒序展示，新增跟进自动刷新列表「最后联系」字段
- **筛选排序**：按公司名/联系人/电话搜索，按标签、阶段过滤，按最近联系/公司名/下次跟进排序
- **提醒功能**：启动弹窗展示今日待跟进 + 已过期客户，列表中过期项红色高亮
- **CSV 导入导出**：导入时按「公司名称」合并更新（同公司非空字段合并，标签去重合并），不会整表覆盖
- **示例数据**：首次启动自动建库并插入 5 家示例客户方便演示

## 目录结构

```
.
├── main.py                  # 入口
├── models.py                # 数据模型层（Customer / FollowUp dataclass）
├── database.py              # 数据访问层（SQLite CRUD + CSV 导入导出）
├── ui/
│   ├── main_window.py       # 主窗口 + 菜单栏
│   ├── customer_list.py     # 左侧客户列表面板
│   ├── customer_detail.py   # 中间客户详情面板
│   ├── timeline.py          # 右侧沟通时间线面板
│   └── dialogs.py           # 今日待跟进等对话框
├── requirements.txt
└── README.md
```

运行后会在当前目录生成 `customers.db`。

## 环境要求

- Windows 10 / 11（也支持 macOS / Linux）
- Python 3.10 及以上

## 安装 & 运行

```bash
# 1. 创建虚拟环境（推荐但非必须）
python -m venv venv
venv\Scripts\activate       # Windows PowerShell
# source venv/bin/activate  # macOS / Linux

# 2. 安装依赖
pip install -r requirements.txt

# 3. 启动
python main.py
```

首次启动会自动创建 `customers.db` 并写入示例数据。

## CSV 格式

列名支持中文或英文表头（识别任意一种即可），顺序不限：

| 中文表头 | 英文表头（兼容） | 说明 |
|---|---|---|
| 公司名称 | company | 必填，合并更新的匹配键 |
| 联系人 | contact | |
| 电话 | phone | |
| 阶段 | stage | 初步接触 / 需求沟通 / 方案报价 / 商务谈判 / 合同签署 / 项目交付 / 已流失 |
| 标签 | tags | 多个标签用英文逗号分隔，导入时自动去重合并 |
| 下次跟进日期 | next_follow_up | YYYY-MM-DD |
| 最后联系时间 | last_contacted | YYYY-MM-DD HH:MM:SS |
| 创建时间 | created_at | （仅导出，导入时忽略） |

编码使用 **UTF-8 with BOM**，Excel 直接打开不乱码。

## 打包成单 EXE（Windows）

推荐用 **PyInstaller**，思路如下：

```bash
# 安装打包工具
pip install pyinstaller

# 打包（单文件、无控制台、可选自定义图标）
pyinstaller --onefile --noconsole --name StudioCRM main.py

# 如果有自定义图标（.ico）
# pyinstaller --onefile --noconsole --name StudioCRM --icon app.ico main.py
```

打包完成后在 `dist/StudioCRM.exe` 就是单文件可执行程序，拷到任意 Windows 10 电脑双击即可运行。首次运行会在 exe 同目录创建 `customers.db`。

如果想把数据库固定到用户目录（避免和 exe 混在一起），可以修改 `database.py` 里的 `DB_PATH`，例如：

```python
import os
DB_PATH = os.path.join(os.path.expanduser("~"), ".studiocrm", "customers.db")
```

## 常用快捷键

| 快捷键 | 功能 |
|---|---|
| Ctrl+I | 导入 CSV |
| Ctrl+E | 导出 CSV |
| Ctrl+T | 打开今日待跟进 |
| Ctrl+Q | 退出 |

## 许可证

内部使用，随便改。
