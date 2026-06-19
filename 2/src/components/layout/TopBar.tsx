import { useScheduleStore } from '../../store/scheduleStore';
import { getWeekDates, formatShortDate, formatWeekday, isToday, parseISO } from '../../utils/dateUtils';

const viewOptions: { key: 'board' | 'calendar'; label: string; icon: string }[] = [
  { key: 'board', label: '看板视图', icon: '🗂️' },
  { key: 'calendar', label: '周历视图', icon: '📅' },
];

export function TopBar() {
  const weekStart = useScheduleStore((s) => s.currentWeekStart);
  const viewMode = useScheduleStore((s) => s.viewMode);
  const setViewMode = useScheduleStore((s) => s.setViewMode);
  const prevWeek = useScheduleStore((s) => s.goToPrevWeek);
  const nextWeek = useScheduleStore((s) => s.goToNextWeek);
  const today = useScheduleStore((s) => s.goToCurrentWeek);

  const weekDates = getWeekDates(parseISO(weekStart));
  const first = weekDates[0];
  const last = weekDates[6];
  const rangeLabel = `${formatShortDate(first)} - ${formatShortDate(last)}`;
  const weekNum = Math.ceil((first.getDate() + new Date(first.getFullYear(), first.getMonth(), 1).getDay()) / 7);

  return (
    <header className="h-16 border-b border-base-200 bg-white/90 backdrop-blur px-6 flex items-center justify-between gap-4 shrink-0 z-10">
      <div className="flex items-center gap-3 min-w-0">
        <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-mint-400 to-sage-500 flex items-center justify-center text-white text-lg shadow-sm">
          🧫
        </div>
        <div className="min-w-0">
          <h1 className="text-lg font-bold text-base-900 truncate">实验室仪器排期看板</h1>
          <p className="text-xs text-base-500 truncate">跨仪器协同调度 · 实时同步本地存储</p>
        </div>
      </div>

      <div className="flex items-center gap-2">
        <div className="flex items-center bg-base-100 rounded-lg p-0.5">
          {viewOptions.map((v) => (
            <button
              key={v.key}
              onClick={() => setViewMode(v.key)}
              className={`px-3 py-1.5 rounded-md text-sm transition flex items-center gap-1.5 ${
                viewMode === v.key
                  ? 'bg-white text-mint-700 shadow-sm font-medium'
                  : 'text-base-600 hover:text-base-800'
              }`}
            >
              <span>{v.icon}</span>
              <span className="hidden sm:inline">{v.label}</span>
            </button>
          ))}
        </div>
      </div>

      <div className="flex items-center gap-2 shrink-0">
        <button
          onClick={prevWeek}
          className="w-8 h-8 rounded-md flex items-center justify-center text-base-600 hover:bg-base-100 transition"
          title="上一周"
        >
          ‹
        </button>
        <button
          onClick={today}
          className="px-3 py-1.5 text-sm rounded-md border border-base-200 text-base-700 hover:bg-base-50 transition font-medium"
        >
          本周
        </button>
        <button
          onClick={nextWeek}
          className="w-8 h-8 rounded-md flex items-center justify-center text-base-600 hover:bg-base-100 transition"
          title="下一周"
        >
          ›
        </button>
        <div className="pl-3 border-l border-base-200 text-right">
          <p className="text-sm font-semibold text-base-800">{rangeLabel}</p>
          <p className="text-xs text-base-500">
            {first.getFullYear()}年 · 第{weekNum}周
            <span className="ml-2">
              {weekDates.filter((d) => isToday(d)).map((d) => (
                <span key={d.toISOString()} className="text-mint-600">
                  (今日 {formatShortDate(d)} {formatWeekday(d)})
                </span>
              ))}
            </span>
          </p>
        </div>
      </div>
    </header>
  );
}
