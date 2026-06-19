# 实验室仪器排期看板

基于 **React 18 + TypeScript + Vite** 的实验室仪器排期看板前端 Demo，数据来源为 `public/mock` 下的静态 JSON，状态用 zustand 管理并持久化到 localStorage，刷新不丢失；拖拽改时段/跨仪器列用 dnd-kit；UI 采用 Tailwind 的浅灰 + 青绿风格。

## ✨ 功能速览

- **左侧仪器面板**：按 光谱类 / 色谱类 / 显微类 / 分析类 分组展示 10 台仪器，支持搜索、全选、清空，点选后主区联动筛选
- **双视图切换**：
  - **看板视图**：仪器横向分块，每块纵轴 08:00–20:00 时间轴，横轴一周 7 天
  - **周历视图**：日期列在顶部，仪器行在左侧，形成日历格子视图
- **拖拽调度**（dnd-kit）：
  - 预约卡片可直接上下拖拽改变时段（30 分钟吸附）
  - 可横向拖拽到其它仪器列/其它日期
  - 同一仪器时间重叠自动拦截 + 标红高亮告警
- **右侧抽屉编辑**：
  - 字段：实验名称、负责人、样本数、备注、仪器、日期+开始+结束时间
  - 支持新建 / 修改 / 删除，表单校验，重叠会阻止保存并提示
  - 所有改动写回 zustand store 并同步到 localStorage
- **本地持久化**：
  - 首次打开会从 `public/mock/*.json` 加载 10 台仪器 + 16 条跨两周预约
  - 用户后续的增删改、视图选择、周次、勾选状态会持久化，刷新保持
- **时间工具**：date-fns + 中文本地化

## 🚀 启动

Windows / macOS / Linux 通用：

```bash
npm install
npm run dev
```

默认地址：`http://localhost:5173`

其他命令：

```bash
npm run build   # 类型检查 + 生产构建到 dist/
npm run preview # 本地预览构建产物
```

## 📁 目录职责

```
.
├── public/
│   └── mock/
│       ├── instruments.json    # 10 台仪器静态数据（id/名称/分类/型号/位置/描述）
│       └── reservations.json   # 16 条跨两周预约（含起始时间、负责人、样本数等）
├── src/
│   ├── components/
│   │   ├── common/
│   │   │   └── ReservationCard.tsx      # 预约卡片（dnd-kit 可拖拽，重叠标红）
│   │   ├── drawer/
│   │   │   └── EditingDrawer.tsx        # 右侧抽屉：新建/编辑预约表单
│   │   ├── layout/
│   │   │   ├── TopBar.tsx               # 顶栏：视图切换 + 周次导航
│   │   │   └── MainViewport.tsx         # 主区容器：负责根据 viewMode 切视图
│   │   ├── sidebar/
│   │   │   └── InstrumentSidebar.tsx    # 左侧仪器分组列表（分类/搜索/勾选）
│   │   └── views/
│   │       ├── BoardView.tsx            # 看板视图：按仪器分块 + 7 天时间列（含 dnd-kit）
│   │       └── CalendarView.tsx         # 周历视图：日期在顶，仪器在侧（含 dnd-kit）
│   ├── hooks/
│   │   └── useMockDataLoader.ts         # 首次加载 public/mock JSON 并合并到 store
│   ├── store/
│   │   └── scheduleStore.ts             # zustand store（含 persist 到 localStorage）
│   ├── types/
│   │   └── index.ts                     # 全局类型（Instrument/Reservation/ViewMode...）
│   ├── utils/
│   │   └── dateUtils.ts                 # 时间计算工具（周/时段/重叠检测/吸附等）
│   ├── App.tsx                          # 应用根组件（layout 组合 + loading/错误态）
│   ├── main.tsx                         # React 入口
│   └── index.css                        # Tailwind 基础样式 + 自定义滚动条
├── index.html                           # Vite HTML 模板（含 Inter 字体）
├── tailwind.config.js                   # Tailwind 配置（浅灰 base + 青绿 mint/sage）
├── postcss.config.js
├── vite.config.ts
├── tsconfig.json / tsconfig.node.json
└── package.json
```

### 关键模块说明

| 模块 | 说明 |
| --- | --- |
| `public/mock/*.json` | 原始数据，只在首屏（localStorage 为空）时作为默认值 |
| `scheduleStore.ts` | 全局唯一数据源。`persist` 中间件会把 `reservations / selectedInstrumentIds / currentWeekStart / viewMode` 持久化到 `localStorage['lab-scheduler-state']` |
| `dateUtils.ts` | 统一的 30 分钟吸附、时段计算、重叠检测、中文格式化；`hasOverlap` 是拦截重叠的核心函数 |
| `BoardView` / `CalendarView` | 均自包含一套 `DndContext`；通过 `document.elementFromPoint` + 自定义 `data-*` 属性定位拖放目标，再计算 slot index 得到新的开始时间，最后调用 store 的 `moveReservationTo`（内含重叠拦截与吸附/夹取逻辑） |
| `EditingDrawer` | 受控表单，保存时先走 `validate` 再调用 `createReservation` / `updateReservation`，重叠会在 store 层二次兜底拦截 |

## 🗂️ Mock 数据规模

- **仪器**：10 台，4 种分类，跨 4 个楼栋
- **预约**：16 条，分布在 `2026-06-15 ~ 2026-06-27` 两周内，覆盖 8 台仪器，包含不同时长（1–7.5h）、不同负责人与样本数

## 🎨 主题色

- 浅灰：`base-50/100/200...` 用作背景、边框、次级文字
- 青绿：`mint-500`（#14b8a6）/ `sage-500`（#689668）用作主按钮、选中态、今日高亮

## 🔐 重叠/冲突策略

- **拖拽时**：store 的 `moveReservationTo` 会先把时间按 30 min 吸附并夹取到 08:00–20:00，再在目标仪器的预约中检查是否与已存在的区间重叠，是则拒绝更新并返回 `overlapped: true`
- **卡片样式**：`findOverlapsOnInstrument` 会在每台仪器内两两比较所有预约，把重叠的卡片 ID 集合返回，用于卡片标红边框和“⚠ 重叠”标签
- **抽屉保存**：同样调用 `hasOverlap`，重叠会以红色提示框阻塞保存
