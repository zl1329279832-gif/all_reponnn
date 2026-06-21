# 番茄钟 Pomodoro

基于 PySide6 的桌面专注力番茄钟应用。

## 功能

- 大号圆环倒计时
- 任务标签 + 时长预设
- 系统托盘图标，最小化后继续计时
- 到点桌面通知 + 提示音
- 本地 SQLite 存储任务记录和每日统计
- 近七天番茄完成数柱状图
- 设置：工作/休息时长、严格模式、开机自启配置、提示音开关
- 三种结束方式：暂停 / 放弃 / 完成（放弃不计入完成数）

## 安装

```powershell
cd 项目根目录
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Windows 启动

```powershell
.venv\Scripts\Activate.ps1
python main.py
```

或（未使用虚拟环境）：

```powershell
pip install -r requirements.txt
python main.py
```

## 开机自启说明

设置页勾选"开机自动启动（仅记录配置）"后，配置项会写入
`%USERPROFILE%\.pomodoro_app\settings.json`。如需真正开机自启，
手动把 `pythonw.exe 路径\main.py` 加入 Windows 启动文件夹即可
（Win+R 输入 `shell:startup`）。本应用不修改注册表。

## 数据存储位置

```
%USERPROFILE%\.pomodoro_app\
  settings.json
  pomodoro.db
```

## 测试

```powershell
pytest tests/ -v
```
