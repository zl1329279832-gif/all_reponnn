import { useScheduleStore } from '../../store/scheduleStore';
import { BoardView } from '../views/BoardView';
import { CalendarView } from '../views/CalendarView';

export function MainViewport() {
  const viewMode = useScheduleStore((s) => s.viewMode);
  const openDrawer = useScheduleStore((s) => s.openDrawer);
  const instruments = useScheduleStore((s) => s.instruments);

  return (
    <main className="flex-1 flex flex-col min-w-0 bg-base-100/60 overflow-hidden">
      <div className="px-4 py-2 border-b border-base-200 bg-white/70 backdrop-blur flex items-center justify-between gap-2 shrink-0">
        <div className="flex items-center gap-2 text-xs text-base-600">
          <span className="inline-flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-mint-500" /> 可拖拽卡片改时段或跨仪器列
          </span>
          <span className="opacity-50">·</span>
          <span>重叠自动拦截并标红</span>
        </div>
        <button
          onClick={() => openDrawer()}
          disabled={instruments.length === 0}
          className="px-3 py-1.5 rounded-md text-xs font-medium text-white bg-gradient-to-r from-mint-500 to-sage-500 hover:from-mint-600 hover:to-sage-600 shadow-sm transition disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-1"
        >
          <span>＋</span>
          <span>新建预约</span>
        </button>
      </div>

      <div className="flex-1 min-h-0 overflow-auto scrollbar-thin">
        {viewMode === 'board' ? <BoardView /> : <CalendarView />}
      </div>
    </main>
  );
}
