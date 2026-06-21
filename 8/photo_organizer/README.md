# 照片整理工具

本地照片整理桌面应用，基于 Python + CustomTkinter 构建。

## 功能

- 指定根文件夹后台扫描 JPG/PNG，读取 EXIF 拍摄时间和相机型号
- 左侧按年月分组展示缩略图网格，右侧查看大图和完整元数据
- 支持修改标题/备注，保存到 SQLite 索引（不修改原文件字节）
- 顶部搜索框按文件名、备注、日期范围过滤，结果实时刷新
- 批量操作：移动到指定相册目录、按拍摄日期重命名（含预览和确认）
- 扫描使用独立线程，界面不假死，底部进度条实时显示
- 配置记忆上次打开的目录，关闭后重新打开仍在

## Windows 下运行

### 1. 安装 Python

确保已安装 Python 3.9+，可在 [python.org](https://www.python.org/downloads/) 下载。
安装时勾选 **"Add Python to PATH"**。

### 2. 安装依赖

打开 PowerShell 或 CMD，进入项目目录：

```powershell
cd photo_organizer
pip install -r requirements.txt
```

### 3. 运行

```powershell
python main.py
```

## 没有 EXIF 的图片处理

本工具对没有 EXIF 信息的图片采用**文件修改时间（mtime）兜底**策略：

1. 优先读取 EXIF 中的 `DateTimeOriginal`、`DateTime`、`DateTimeDigitized` 字段作为拍摄时间
2. 如果以上字段均不存在或无法解析，则使用文件的修改时间（`os.stat().st_mtime`）作为拍摄时间
3. 无 EXIF 的图片，相机型号字段留空

这意味着：
- 手机截图、网络下载的无 EXIF 图片仍可按修改时间排序和分组
- 直接从相机导出的 RAW 转 JPG 若丢失 EXIF，也可通过修改时间兜底
- 缩略图仍会正常生成，不影响浏览

## 项目结构

```
photo_organizer/
├── main.py              # 入口
├── config.py            # 配置持久化
├── database.py          # SQLite 索引
├── scanner.py           # 后台扫描 + EXIF 读取 + 批量操作
├── ui/
│   ├── __init__.py
│   ├── app.py           # 主窗口
│   ├── sidebar.py       # 左侧缩略图网格
│   ├── detail.py        # 右侧大图 + 元数据 + 编辑
│   ├── search.py        # 顶部搜索栏
│   ├── progress.py      # 底部进度条
│   └── batch.py         # 批量操作对话框
├── requirements.txt
└── README.md
```

## 数据存储位置

- SQLite 数据库：`~/.photo_organizer/photos.db`
- 缩略图缓存：`~/.photo_organizer/thumbnails/`
- 配置文件：`~/.photo_organizer/config.json`

所有元数据仅保存在本地 SQLite 中，**不会修改原始照片文件的任何字节**。
