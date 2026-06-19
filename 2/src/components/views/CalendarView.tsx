import { useMemo, useState } from 'react';
import {
  DndContext,
  DragOverlay,
  closestCorners,
  PointerSensor,
  useSensor,
  useSensors,
  type DragStartEvent,
  type DragOverEvent,
  type DragEndEvent,
} from '@dnd-kit/core';
import { useScheduleStore } from '../../store/scheduleStore';
import { ReservationCard } from '../common/ReservationCard';
import type { Reservation, Instrument } from '../../types';
import {
  getWeekDates,
  parseISO,
  isSameDay,
  formatWeekday,
  formatShortDate,
  isToday,
  DAY_START_HOUR,
  DAY_END_HOUR,
  SLOT_MINUTES,
  differenceInMinutes,
  addMinutes,
  startOfDay,
  setHours,
  setMinutes,
} from '../../utils/dateUtils';

interface CellDroppable {
  instrumentId: string;
  day: Date;
}

export function CalendarView() {
  const instruments = useScheduleStore((s) => s.instruments);
  const allReservations = useScheduleStore((s) => s.reservations);
  const selectedIds = useScheduleStore((s) => s.selectedInstrumentIds);
  const weekStart = useScheduleStore((s) => s.currentWeekStart);
  const findOverlaps = useScheduleStore((s) => s.findOverlapsOnInstrument);
  const moveReservation = useScheduleStore((s) => s.moveReservationTo);
  const openDrawer = useScheduleStore((s) => s.openDrawer);

  const weekDates = getWeekDates(parseISO(weekStart));
  const totalSlots = ((DAY_END_HOUR - DAY_START_HOUR) * 60) / SLOT_MINUTES;

  const [activeId, setActiveId] = useState<string | null>(null);
  const [preview, setPreview] = useState<{
    instrumentId: string;
    day: Date;
    slotIdx: number;
  } | null>(null);

  const pointerSensor = useSensor(PointerSensor, {
    activationConstraint: { distance: 5 },
  });
  const sensors = useSensors(pointerSensor);

  const selectedInstruments = useMemo(() => {
    return selectedIds.length > 0
      ? instruments.filter((i) => selectedIds.includes(i.id))
      : instruments;
  }, [instruments, selectedIds]);

  const activeReservation = activeId
    ? allReservations.find((r) => r.id === activeId)
    : null;

  const overlapsByInst = useMemo(() => {
    const map = new Map<string, string[]>();
    for (const inst of selectedInstruments) {
      map.set(inst.id, findOverlaps(inst.id));
    }
    return map;
  }, [selectedInstruments, findOverlaps]);

  function handleDragStart(e: DragStartEvent) {
    setActiveId(String(e.active.id));
  }

  function handleDragOver(e: DragOverEvent) {
    const ev = e.activatorEvent as PointerEvent;
    const el = document.elementFromPoint(ev.clientX, ev.clientY);
    const cell = el?.closest('[data-cal-cell="true"]') as HTMLElement | null;
    if (!cell) return;
    const instId = cell.dataset.instrumentId;
    const dateStr = cell.dataset.dayDate;
    if (!instId || !dateStr) return;
    const rect = cell.getBoundingClientRect();
    const y = ev.clientY - rect.top;
    const slotHeight = rect.height / totalSlots;
    const slotIdx = Math.max(0, Math.min(totalSlots - 1, Math.floor(y / slotHeight)));
    setPreview({ instrumentId: instId, day: parseISO(dateStr), slotIdx });
  }

  function handleDragEnd(e: DragEndEvent) {
    const resId = String(e.active.id);
    const reservation = allReservations.find((r) => r.id === resId);
    setActiveId(null);
    const target = preview;
    setPreview(null);
    if (!reservation || !target) return;
    const durMin = differenceInMinutes(parseISO(reservation.endTime), parseISO(reservation.startTime));
    const base = setMinutes(setHours(startOfDay(target.day), DAY_START_HOUR), 0);
    const newStart = addMinutes(base, target.slotIdx * SLOT_MINUTES);
    const newEnd = addMinutes(newStart, durMin);
    moveReservation(resId, target.instrumentId, newStart.toISOString(), newEnd.toISOString());
  }

  function renderSlotRows() {
    const rows = [];
    for (let h = DAY_START_HOUR; h < DAY_END_HOUR; h++) {
      for (let half = 0; half < 2; half++) {
        const isHour = half === 0;
        const label = isHour ? `${String(h).padStart(2, '0')}:00` : '';
        rows.push(
          <div
            key={`${h}-${half}`}
            className={`border-b border-base-100 ${isHour ? 'border-base-200' : ''}`}
            style={{ height: `${100 / totalSlots}%` }}
          >
            {label && (
              <div className="text-[10px] text-base-500 text-right pr-2 pt-0.5">{label}</div>
            )}
          </div>
        );
      }
    }
    return rows;
  }

  function renderCell(inst: Instrument, day: Date) {
    const cellInstOverlaps = overlapsByInst.get(inst.id) ?? [];
    const cellReservations = allReservations.filter(
      (r) => r.instrumentId === inst.id && isSameDay(parseISO(r.startTime), day)
    );
    const isActiveCell =
      preview && preview.instrumentId === inst.id && isSameDay(preview.day, day);
    return (
      <div
        key={`${inst.id}-${day.toISOString()}`}
        data-cal-cell="true"
        data-instrument-id={inst.id}
        data-day-date={day.toISOString()}
        className={`relative border-l border-base-200 first:border-l-0 min-h-0 ${
          isActiveCell ? 'bg-mint-50/40' : 'bg-white'
        }`}
        style={{ flex: '1 1 0', minWidth: '140px' }}
      >
        {Array.from({ length: totalSlots }, (_, i) => {
          const isHour = i % 2 === 0;
          return (
            <div
              key={i}
              className={`border-b ${isHour ? 'border-base-100' : 'border-base-50'}`}
              style={{ height: `${100 / totalSlots}%` }}
            />
          );
        })}

        {isActiveCell && preview && (
          <div
            className="absolute left-1 right-1 border-2 border-dashed border-mint-500 bg-mint-100/40 rounded-lg pointer-events-none z-10"
            style={{
              top: `${(preview.slotIdx / totalSlots) * 100}%`,
              height: `${(2 / totalSlots) * 100}%`,
            }}
          />
        )}

        {cellReservations.map((r) => {
          const colBaseMin = setMinutes(
            setHours(startOfDay(day), DAY_START_HOUR),
            0
          ).getTime();
          const offsetMin = (parseISO(r.startTime).getTime() - colBaseMin) / 60000;
          const durMin = differenceInMinutes(parseISO(r.endTime), parseISO(r.startTime));
          const top = Math.max(0, (offsetMin / (totalSlots * SLOT_MINUTES)) * 100);
          const height = (durMin / (totalSlots * SLOT_MINUTES)) * 100;
          return (
            <div
              key={r.id}
              className="absolute left-1 right-1 z-20"
              style={{
                top: `${top}%`,
                height: `${height}%`,
                minHeight: '28px',
              }}
            >
              <ReservationCard
                reservation={r}
                isOverlapping={cellInstOverlaps.includes(r.id)}
                compact={height < 0.08}
                onClick={() => openDrawer(r.id)}
              />
            </div>
          );
        })}
      </div>
    );
  }

  return (
    <DndContext
      sensors={sensors}
      collisionDetection={closestCorners}
      onDragStart={handleDragStart}
      onDragOver={handleDragOver}
      onDragEnd={handleDragEnd}
      onDragCancel={() => {
        setActiveId(null);
        setPreview(null);
      }}
    >
      <div className="flex-1 flex flex-col min-h-0 overflow-hidden bg-white">
        {selectedInstruments.length === 0 ? (
          <div className="flex-1 flex items-center justify-center text-base-500">
            <div className="text-center space-y-2">
              <p className="text-4xl">📅</p>
              <p>请在左侧勾选至少一台仪器</p>
            </div>
          </div>
        ) : (
          <div className="flex-1 flex flex-col min-h-0">
            <div className="flex shrink-0 border-b border-base-200 bg-base-50 sticky top-0 z-30">
              <div className="w-28 shrink-0" />
              <div className="flex flex-1 min-w-0">
                {weekDates.map((day) => (
                  <div
                    key={day.toISOString()}
                    className={`px-2 py-2 text-center border-l border-base-200 first:border-l-0 flex-1 ${
                      isToday(day) ? 'bg-mint-50' : ''
                    }`}
                    style={{ minWidth: '140px' }}
                  >
                    <p className={`text-xs font-semibold ${isToday(day) ? 'text-mint-700' : 'text-base-700'}`}>
                      {formatWeekday(day)}
                    </p>
                    <p className={`text-sm font-bold ${isToday(day) ? 'text-mint-600' : 'text-base-800'}`}>
                      {formatShortDate(day)}
                      {isToday(day) && (
                        <span className="ml-1 inline-block w-1.5 h-1.5 rounded-full bg-mint-500 align-middle" />
                      )}
                    </p>
                  </div>
                ))}
              </div>
            </div>

            <div className="flex-1 flex flex-col min-h-0 overflow-hidden">
              {selectedInstruments.map((inst) => (
                <div
                  key={inst.id}
                  className="flex border-b border-base-200 last:border-b-0 min-h-0"
                  style={{ flex: '1 1 0', minHeight: '220px' }}
                >
                  <div className="w-28 shrink-0 border-r border-base-200 bg-gradient-to-b from-sage-50 to-mint-50 p-2 flex flex-col">
                    <p className="text-xs font-semibold text-base-800 leading-snug line-clamp-3">
                      {inst.name}
                    </p>
                    <p className="text-[10px] text-base-500 mt-1">{inst.model}</p>
                    <p className="text-[10px] text-base-400 mt-auto">{inst.location}</p>
                  </div>
                  <div className="flex-1 flex min-w-0 relative overflow-x-auto scrollbar-thin">
                    {weekDates.map((day) => renderCell(inst, day))}
                  </div>
                </div>
              ))}

              <div className="absolute left-0 top-12 pointer-events-none w-28">
                {/* placeholder */}
              </div>
            </div>

            <div className="hidden">{renderSlotRows()}</div>
          </div>
        )}
      </div>

      <DragOverlay>
        {activeReservation && (
          <div style={{ width: '220px', opacity: 0.95 }}>
            <ReservationCard reservation={activeReservation} disableDrag />
          </div>
        )}
      </DragOverlay>
    </DndContext>
  );
}
