import { useMemo, useState } from 'react';
import { useScheduleStore } from '../../store/scheduleStore';
import type { Instrument, InstrumentCategory } from '../../types';

const categoryOrder: InstrumentCategory[] = ['光谱类', '色谱类', '显微类', '分析类'];

const categoryIcon: Record<InstrumentCategory, string> = {
  '光谱类': '🧪',
  '色谱类': '⚗️',
  '显微类': '🔬',
  '分析类': '📊',
};

export function InstrumentSidebar() {
  const instruments = useScheduleStore((s) => s.instruments);
  const selectedIds = useScheduleStore((s) => s.selectedInstrumentIds);
  const toggleInstrument = useScheduleStore((s) => s.toggleInstrument);
  const selectAll = useScheduleStore((s) => s.selectAllInstruments);
  const clearAll = useScheduleStore((s) => s.clearInstrumentSelection);
  const getReservations = useScheduleStore((s) => s.getInstrumentReservations);
  const reservations = useScheduleStore((s) => s.reservations);

  const [keyword, setKeyword] = useState('');

  const grouped = useMemo(() => {
    const groups: Partial<Record<InstrumentCategory, Instrument[]>> = {};
    const filtered = instruments.filter(
      (i) =>
        !keyword ||
        i.name.toLowerCase().includes(keyword.toLowerCase()) ||
        i.model.toLowerCase().includes(keyword.toLowerCase())
    );
    for (const cat of categoryOrder) groups[cat] = [];
    for (const ins of filtered) {
      if (groups[ins.category]) groups[ins.category]!.push(ins);
    }
    return groups;
  }, [instruments, keyword]);

  const countByInstrument = useMemo(() => {
    const map = new Map<string, number>();
    for (const r of reservations) {
      map.set(r.instrumentId, (map.get(r.instrumentId) ?? 0) + 1);
    }
    return map;
  }, [reservations]);

  const totalCount = instruments.length;
  const selectedCount = selectedIds.length;

  return (
    <aside className="w-72 shrink-0 h-full border-r border-base-200 bg-white flex flex-col">
      <div className="px-5 py-4 border-b border-base-200">
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-base-900 font-semibold text-lg">仪器列表</h2>
          <span className="text-xs text-base-500">
            {selectedCount}/{totalCount} 选中
          </span>
        </div>
        <div className="flex gap-2 mb-3">
          <button
            onClick={selectAll}
            className="flex-1 text-xs py-1.5 rounded-md bg-sage-100 text-sage-700 hover:bg-sage-200 transition"
          >
            全选
          </button>
          <button
            onClick={clearAll}
            className="flex-1 text-xs py-1.5 rounded-md bg-base-100 text-base-600 hover:bg-base-200 transition"
          >
            清空
          </button>
        </div>
        <div className="relative">
          <input
            type="text"
            value={keyword}
            onChange={(e) => setKeyword(e.target.value)}
            placeholder="搜索仪器名称 / 型号..."
            className="w-full text-sm px-3 py-2 pl-8 rounded-lg border border-base-200 bg-base-50 focus:outline-none focus:ring-2 focus:ring-mint-400 focus:bg-white transition"
          />
          <span className="absolute left-2.5 top-1/2 -translate-y-1/2 text-base-400 text-sm">
            🔍
          </span>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto scrollbar-thin px-3 py-3 space-y-4">
        {categoryOrder.map((cat) => {
          const items = grouped[cat];
          if (!items || items.length === 0) return null;
          return (
            <div key={cat}>
              <div className="flex items-center gap-2 px-2 py-1.5">
                <span className="text-lg">{categoryIcon[cat]}</span>
                <span className="text-xs font-semibold text-base-600 uppercase tracking-wider">
                  {cat}
                </span>
                <span className="text-[10px] text-base-400 bg-base-100 px-1.5 py-0.5 rounded-full ml-auto">
                  {items.length}
                </span>
              </div>
              <ul className="mt-1 space-y-1">
                {items.map((ins) => {
                  const checked = selectedIds.includes(ins.id);
                  const count = countByInstrument.get(ins.id) ?? 0;
                  return (
                    <li key={ins.id}>
                      <button
                        onClick={() => toggleInstrument(ins.id)}
                        className={`w-full text-left px-3 py-2.5 rounded-lg border transition flex items-start gap-3 group ${
                          checked
                            ? 'border-mint-400 bg-mint-50 shadow-sm'
                            : 'border-transparent hover:border-base-200 hover:bg-base-50'
                        }`}
                      >
                        <span
                          className={`mt-0.5 w-4 h-4 shrink-0 rounded border flex items-center justify-center transition ${
                            checked
                              ? 'bg-mint-500 border-mint-500 text-white'
                              : 'border-base-300 group-hover:border-base-400 bg-white'
                          }`}
                        >
                          {checked && <span className="text-[10px] leading-none">✓</span>}
                        </span>
                        <div className="min-w-0 flex-1">
                          <div className="flex items-start justify-between gap-1">
                            <p
                              className={`text-sm font-medium truncate ${
                                checked ? 'text-mint-800' : 'text-base-800'
                              }`}
                            >
                              {ins.name}
                            </p>
                            {count > 0 && (
                              <span className="shrink-0 text-[10px] px-1.5 py-0.5 rounded-full bg-base-200 text-base-600">
                                {count}
                              </span>
                            )}
                          </div>
                          <p className="text-xs text-base-500 mt-0.5 truncate">
                            {ins.model} · {ins.location}
                          </p>
                        </div>
                      </button>
                    </li>
                  );
                })}
              </ul>
            </div>
          );
        })}
      </div>

      <div className="border-t border-base-200 px-5 py-3 text-xs text-base-500 bg-base-50">
        点击仪器卡片筛选主区显示
      </div>
    </aside>
  );
}
