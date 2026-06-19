import { useMemo } from 'react';
import {
  DndContext,
  DragOverlay,
  closestCorners,
  PointerSensor,
  useSensor,
  useSensors,
  type DragEndEvent,
  type DragStartEvent,
  type DragOverEvent,
} from '@dnd-kit/core';
import { useScheduleStore } from '../../store/scheduleStore';
import { ReservationCard } from '../common/ReservationCard';
import type { Instrument, Reservation } from '../../types';
import {
  getWeekDates,
  parseISO,
  isSameDay,
  formatDateLabel,
  isToday,
  DAY_START_HOUR,
  DAY_END_HOUR,
  SLOT_MINUTES,
  differenceInMinutes,
  formatTime,
  addMinutes,
  startOfDay,
  setHours,
  setMinutes,
} from '../../utils/dateUtils';
import { useState } from 'react';

interface DropTargetData {
  instrumentId: string;
  dayIndex: number;
  slotIndex?: number;
  isColumn?: boolean;
}

function InstrumentDayColumn({
  instrument,
  day,
  reservations,
  weekStartISO,
  onDropPreview,
  activeId,
  overlappedIds,
  onCardClick,
}: {
  instrument: Instrument;
  day: Date;
  reservations: Reservation[];
  weekStartISO: string;
  onDropPreview?: (slotIdx: number) => void;
  activeId: string | null;
  overlappedIds: string[];
  onCardClick: (id: string) => void;
}) {
  const totalSlots = ((DAY_END_HOUR - DAY_START_HOUR) * 60) / SLOT_MINUTES;
  const colStartMin = 0;

  const slots = useMemo(() => {
    return Array.from({ length: totalSlots }, (_, i) => i);
  }, [totalSlots]);

  const [hoverSlot, setHoverSlot] = useState<number | null>(null);

  const handleDropZoneMouseMove = (e: React.MouseEvent<HTMLDivElement>) => {
    if (!activeId) return;
    const rect = e.currentTarget.getBoundingClientRect();
    const y = e.clientY - rect.top;
    const slotHeight = rect.height / totalSlots;
    const idx = Math.max(0, Math.min(totalSlots - 1, Math.floor(y / slotHeight)));
    setHoverSlot(idx);
    onDropPreview?.(idx);
  };

  const handleMouseLeave = () => {
    setHoverSlot(null);
  };

  return (
    <div
      className="relative flex flex-col h-full border-l border-base-200 first:border-l-0 min-w-[220px]"
      onMouseMove={handleDropZoneMouseMove}
      onMouseLeave={handleMouseLeave}
      data-droppable="true"
      data-instrument-id={instrument.id}
      data-day-date={day.toISOString()}
    >
      <div className="px-2 py-2 bg-base-50 border-b border-base-200 text-center">
        <p className={`text-[11px] ${isToday(day) ? 'text-mint-600 font-bold' : 'text-base-500'}`}>
          {formatDateLabel(day)}
          {isToday(day) && <span className="ml-1 inline-block w-1.5 h-1.5 rounded-full bg-mint-500 align-middle" />}
        </p>
      </div>

      <div className="relative flex-1 overflow-hidden bg-white">
        {slots.map((idx) => {
          const isHour = idx % 2 === 0;
          return (
            <div
              key={idx}
              className={`border-b ${isHour ? 'border-base-100' : 'border-base-50'} ${
                hoverSlot === idx ? 'bg-mint-50/60' : ''
              }`}
              style={{ height: `${100 / totalSlots}%` }}
            />
          );
        })}

        {hoverSlot !== null && (
          <div
            className="absolute left-1 right-1 border-2 border-dashed border-mint-500 bg-mint-100/40 rounded-lg pointer-events-none"
            style={{
              top: `${(hoverSlot / totalSlots) * 100}%`,
              height: `${(2 / totalSlots) * 100}%`,
            }}
          />
        )}

        {reservations.map((r) => {
          const rStart = parseISO(r.startTime);
          if (!isSameDay(rStart, day)) return null;
          const colBaseMin = setMinutes(setHours(startOfDay(day), DAY_START_HOUR), 0).getTime();
          const offsetMin = (parseISO(r.startTime).getTime() - colBaseMin) / 60000;
          const durMin = differenceInMinutes(parseISO(r.endTime), parseISO(r.startTime));
          const top = Math.max(0, (offsetMin / (totalSlots * SLOT_MINUTES)) * 100);
          const height = (durMin / (totalSlots * SLOT_MINUTES)) * 100;
          return (
            <div
              key={r.id}
              className="absolute left-1 right-1"
              style={{ top: `${top}%`, height: `${height}%`, minHeight: '32px' }}
            >
              <ReservationCard
                reservation={r}
                isOverlapping={overlappedIds.includes(r.id)}
                compact={height < 0.08}
                onClick={() => onCardClick(r.id)}
              />
            </div>
          );
        })}
      </div>
    </div>
  );
}

export function BoardView() {
  const instruments = useScheduleStore((s) => s.instruments);
  const allReservations = useScheduleStore((s) => s.reservations);
  const selectedIds = useScheduleStore((s) => s.selectedInstrumentIds);
  const weekStart = useScheduleStore((s) => s.currentWeekStart);
  const findOverlaps = useScheduleStore((s) => s.findOverlapsOnInstrument);
  const moveReservation = useScheduleStore((s) => s.moveReservationTo);
  const openDrawer = useScheduleStore((s) => s.openDrawer);

  const weekDates = getWeekDates(parseISO(weekStart));

  const [activeId, setActiveId] = useState<string | null>(null);
  const [previewSlot, setPreviewSlot] = useState<{
    instrumentId: string;
    day: Date;
    slotIdx: number;
  } | null>(null);

  const pointerSensor = useSensor(PointerSensor, {
    activationConstraint: {
      distance: 5,
    },
  });
  const sensors = useSensors(pointerSensor);

  const selectedInstruments = useMemo(() => {
    const base = selectedIds.length > 0 ? instruments.filter((i) => selectedIds.includes(i.id)) : instruments;
    return base;
  }, [instruments, selectedIds]);

  const activeReservation = activeId
    ? allReservations.find((r) => r.id === activeId)
    : null;

  function handleDragStart(e: DragStartEvent) {
    setActiveId(String(e.active.id));
  }

  function handleDragOver(e: DragOverEvent) {
    const over = e.over;
    if (!over) return;
    const el = document.elementFromPoint(
      (e.activatorEvent as PointerEvent).clientX,
      (e.activatorEvent as PointerEvent).clientY
    );
    const column = el?.closest('[data-droppable="true"]') as HTMLElement | null;
    if (!column) return;
    const instId = column.dataset.instrumentId;
    const dateStr = column.dataset.dayDate;
    if (!instId || !dateStr) return;
    const rect = column.getBoundingClientRect();
    const y = (e.activatorEvent as PointerEvent).clientY - rect.top;
    const totalSlots = ((DAY_END_HOUR - DAY_START_HOUR) * 60) / SLOT_MINUTES;
    const slotHeight = rect.height / totalSlots;
    const slotIdx = Math.max(0, Math.min(totalSlots - 1, Math.floor(y / slotHeight)));
    setPreviewSlot({ instrumentId: instId, day: parseISO(dateStr), slotIdx });
  }

  function handleDragEnd(e: DragEndEvent) {
    const resId = String(e.active.id);
    const reservation = allReservations.find((r) => r.id === resId);
    const target = previewSlot;
    setActiveId(null);
    setPreviewSlot(null);
    if (!reservation || !target) return;

    const durMin = differenceInMinutes(parseISO(reservation.endTime), parseISO(reservation.startTime));
    const base = setMinutes(setHours(startOfDay(target.day), DAY_START_HOUR), 0);
    const newStart = addMinutes(base, target.slotIdx * SLOT_MINUTES);
    const newEnd = addMinutes(newStart, durMin);
    moveReservation(resId, target.instrumentId, newStart.toISOString(), newEnd.toISOString());
  }

  function renderTimeAxis() {
    const totalSlots = ((DAY_END_HOUR - DAY_START_HOUR) * 60) / SLOT_MINUTES;
    const slots = [];
    for (let h = DAY_START_HOUR; h < DAY_END_HOUR; h++) {
      slots.push(
        <div
          key={h}
          className="border-b border-base-200 text-[10px] text-base-500 text-right pr-2 pt-0.5"
          style={{ height: `${(60 / SLOT_MINUTES / totalSlots) * 100 * 2}%` }}
        >
          {String(h).padStart(2, '0')}:00
        </div>
      );
    }
    return slots;
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
        setPreviewSlot(null);
      }}
    >
      <div className="flex-1 flex flex-col min-h-0 overflow-hidden">
        {selectedInstruments.length === 0 ? (
          <div className="flex-1 flex items-center justify-center text-base-500">
            <div className="text-center space-y-2">
              <p className="text-4xl">🧪</p>
              <p>请在左侧勾选至少一台仪器</p>
            </div>
          </div>
        ) : (
          <div className="flex-1 flex flex-col min-h-0">
            {selectedInstruments.map((inst) => {
              const overlappedIdsAll = findOverlaps(inst.id);
              const weekReservations = allReservations.filter(
                (r) =>
                  r.instrumentId === inst.id &&
                  weekDates.some((d) => isSameDay(parseISO(r.startTime), d))
              );
              return (
                <div
                  key={inst.id}
                  className="min-h-0 flex flex-col border-b border-base-200 last:border-b-0 bg-white"
                  style={{ flex: '1 1 0', minHeight: '260px' }}
                >
                  <div className="flex items-center px-4 py-2 border-b border-base-100 bg-gradient-to-r from-sage-50 to-mint-50">
                    <div className="flex items-center gap-2">
                      <span className="w-2 h-2 rounded-full bg-mint-500" />
                      <h3 className="font-semibold text-sm text-base-800">{inst.name}</h3>
                      <span className="text-[11px] text-base-500">{inst.model}</span>
                      <span className="text-[11px] text-base-400">· {inst.location}</span>
                    </div>
                    <div className="ml-auto flex items-center gap-3 text-[11px] text-base-500">
                      <span>本周预约 {weekReservations.length}</span>
                    </div>
                  </div>
                  <div className="flex flex-1 min-h-0">
                    <div className="w-12 shrink-0 border-r border-base-200 bg-base-50/60 pt-10">
                      {renderTimeAxis()}
                    </div>
                    <div className="flex-1 flex min-w-0 overflow-x-auto scrollbar-thin">
                      {weekDates.map((day) => (
                        <InstrumentDayColumn
                          key={`${inst.id}-${day.toISOString()}`}
                          instrument={inst}
                          day={day}
                          reservations={weekReservations.filter((r) =>
                            isSameDay(parseISO(r.startTime), day)
                          )}
                          weekStartISO={weekStart}
                          activeId={activeId}
                          overlappedIds={overlappedIdsAll}
                          onCardClick={(id) => openDrawer(id)}
                        />
                      ))}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      <DragOverlay>
        {activeReservation && (
          <div style={{ width: '240px', opacity: 0.95 }}>
            <ReservationCard reservation={activeReservation} disableDrag />
          </div>
        )}
      </DragOverlay>
    </DndContext>
  );
}
