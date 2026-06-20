import { useMemo, useRef, useState, useCallback } from 'react';
import {
  DndContext,
  DragOverlay,
  closestCenter,
  PointerSensor,
  useSensor,
  useSensors,
  type DragStartEvent,
  type DragOverEvent,
  type DragEndEvent,
} from '@dnd-kit/core';
import { useScheduleStore } from '../../store/scheduleStore';
import { ReservationCard } from '../common/ReservationCard';
import {
  DroppableCell,
  decodeDroppableId,
  type DroppableCellHandle,
} from '../dnd/DroppableCell';
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
  hasOverlap,
} from '../../utils/dateUtils';
import { toast } from '../../store/toastStore';

const TOTAL_SLOTS = ((DAY_END_HOUR - DAY_START_HOUR) * 60) / SLOT_MINUTES;

interface DropTargetWithDuration {
  instrumentId: string;
  day: Date;
  slotIdx: number;
  wouldOverlap: boolean;
  durationSlots: number;
}

function formatDateOnlyISO(d: Date): string {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  return `${y}-${m}-${day}`;
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

  const [activeId, setActiveId] = useState<string | null>(null);
  const [activeReservation, setActiveReservation] =
    useState<Reservation | null>(null);
  const [preview, setPreview] = useState<DropTargetWithDuration | null>(null);

  const slotReports = useRef<
    Map<string, { slotIdx: number }>
  >(new Map());
  const cellHandles = useRef<Map<string, DroppableCellHandle>>(new Map());

  const pointerSensor = useSensor(PointerSensor, {
    activationConstraint: { distance: 5 },
  });
  const sensors = useSensors(pointerSensor);

  const selectedInstruments = useMemo(() => {
    return selectedIds.length > 0
      ? instruments.filter((i) => selectedIds.includes(i.id))
      : instruments;
  }, [instruments, selectedIds]);

  const overlapsByInst = useMemo(() => {
    const map = new Map<string, string[]>();
    for (const inst of selectedInstruments) {
      map.set(inst.id, findOverlaps(inst.id));
    }
    return map;
  }, [selectedInstruments, findOverlaps]);

  const computeSlotIdxByClientY = useCallback(
    (droppableId: string, clientY: number): number => {
      const handle = cellHandles.current.get(droppableId);
      if (handle) return handle.computeSlotIndex(clientY, TOTAL_SLOTS);
      const last = slotReports.current.get(droppableId);
      if (last) return last.slotIdx;
      return 0;
    },
    []
  );

  const computeIfOverlap = useCallback(
    (params: {
      reservationId: string;
      instrumentId: string;
      startTimeISO: string;
      endTimeISO: string;
    }): boolean => {
      const siblings = allReservations.filter(
        (r) =>
          r.instrumentId === params.instrumentId &&
          r.id !== params.reservationId
      );
      return hasOverlap(
        { startTime: params.startTimeISO, endTime: params.endTimeISO },
        siblings
      );
    },
    [allReservations]
  );

  function handleDragStart(e: DragStartEvent) {
    const id = String(e.active.id);
    const r = allReservations.find((x) => x.id === id);
    setActiveId(id);
    setActiveReservation(r ?? null);
    slotReports.current.clear();
  }

  function handleDragOver(e: DragOverEvent) {
    if (!activeReservation) return;
    const over = e.over;
    if (!over) {
      setPreview(null);
      return;
    }
    const meta = decodeDroppableId(String(over.id));
    if (!meta) return;

    const clientY =
      (e.activatorEvent as PointerEvent | undefined)?.clientY ??
      (over.rect as DOMRect | null)?.top ??
      0;

    const slotIdx = computeSlotIdxByClientY(String(over.id), clientY);
    const day = parseISO(`${meta.dayDate}T00:00:00`);
    const base = setMinutes(setHours(startOfDay(day), DAY_START_HOUR), 0);
    const newStart = addMinutes(base, slotIdx * SLOT_MINUTES);
    const durMin = differenceInMinutes(
      parseISO(activeReservation.endTime),
      parseISO(activeReservation.startTime)
    );
    let newEnd = addMinutes(newStart, durMin);
    const maxEnd = setMinutes(setHours(startOfDay(day), DAY_END_HOUR), 0);
    if (newEnd > maxEnd) newEnd = maxEnd;

    const wouldOverlap = computeIfOverlap({
      reservationId: activeReservation.id,
      instrumentId: meta.instrumentId,
      startTimeISO: newStart.toISOString(),
      endTimeISO: newEnd.toISOString(),
    });
    setPreview({
      instrumentId: meta.instrumentId,
      day,
      slotIdx,
      wouldOverlap,
      durationSlots: Math.max(1, Math.round(durMin / SLOT_MINUTES)),
    });
  }

  function handleDragEnd(e: DragEndEvent) {
    const resId = String(e.active.id);
    const reservation = allReservations.find((r) => r.id === resId);
    const over = e.over;

    setActiveId(null);
    setActiveReservation(null);
    const lastPreview = preview;
    setPreview(null);

    if (!reservation) return;
    if (!over) {
      toast('已取消拖放', 'info', 1400);
      return;
    }
    const meta = decodeDroppableId(String(over.id));
    if (!meta) {
      toast('无效的拖放目标', 'warning');
      return;
    }

    const clientY =
      (e.activatorEvent as PointerEvent | undefined)?.clientY ?? 0;
    const slotIdx = lastPreview
      ? lastPreview.slotIdx
      : computeSlotIdxByClientY(String(over.id), clientY);

    const day = parseISO(`${meta.dayDate}T00:00:00`);
    const base = setMinutes(setHours(startOfDay(day), DAY_START_HOUR), 0);
    const newStart = addMinutes(base, slotIdx * SLOT_MINUTES);
    const durMin = differenceInMinutes(
      parseISO(reservation.endTime),
      parseISO(reservation.startTime)
    );
    const newEnd = addMinutes(newStart, durMin);

    const instName =
      instruments.find((i) => i.id === meta.instrumentId)?.name ??
      meta.instrumentId;
    const dateStr = formatDateOnlyISO(day);
    const startStr = `${String(newStart.getHours()).padStart(2, '0')}:${String(
      newStart.getMinutes()
    ).padStart(2, '0')}`;
    const endStr = `${String(newEnd.getHours()).padStart(2, '0')}:${String(
      newEnd.getMinutes()
    ).padStart(2, '0')}`;

    const result = moveReservation(
      resId,
      meta.instrumentId,
      newStart.toISOString(),
      newEnd.toISOString()
    );

    if (result.success) {
      const crossInst = reservation.instrumentId !== meta.instrumentId;
      const crossDay = !isSameDay(parseISO(reservation.startTime), day);
      toast(
        `已调度：${instName} ${dateStr} ${startStr}-${endStr}${
          crossInst ? '（跨仪器）' : ''
        }${crossDay ? '（跨日期）' : ''}`,
        'success',
        2400
      );
    } else if (result.overlapped) {
      toast(
        `时段冲突：${instName} ${dateStr} ${startStr}-${endStr} 已被占用，拦截落位`,
        'error',
        3200
      );
    } else {
      toast('调度失败，请重试', 'error');
    }
  }

  function renderCell(inst: Instrument, day: Date) {
    const dateKey = formatDateOnlyISO(day);
    const dropId = `drop__${inst.id}__${dateKey}`;
    const cellInstOverlaps = overlapsByInst.get(inst.id) ?? [];
    const cellReservations = allReservations.filter(
      (r) => r.instrumentId === inst.id && isSameDay(parseISO(r.startTime), day)
    );
    const activeDrop =
      preview?.instrumentId === inst.id &&
      formatDateOnlyISO(preview.day) === dateKey;
    const showPreviewHere = activeDrop;
    const isOverlap = showPreviewHere && preview!.wouldOverlap;

    return (
      <DroppableCell
        key={dropId}
        instrumentId={inst.id}
        dayDate={dateKey}
        totalSlots={TOTAL_SLOTS}
        onSlotIndexChange={(idx) => {
          slotReports.current.set(dropId, { slotIdx: idx });
        }}
        registerHandle={(h) => {
          if (h) cellHandles.current.set(dropId, h);
          else cellHandles.current.delete(dropId);
        }}
        activeDrop={activeDrop}
        className={`relative border-l border-base-200 first:border-l-0 min-h-0 overflow-hidden ${
          showPreviewHere ? (isOverlap ? 'bg-red-50/60' : 'bg-mint-50/40') : 'bg-white'
        }`}
        style={{ flex: '1 1 0', minWidth: '140px' }}
      >
        {Array.from({ length: TOTAL_SLOTS }, (_, i) => {
          const isHour = i % 2 === 0;
          return (
            <div
              key={i}
              className={`border-b ${isHour ? 'border-base-100' : 'border-base-50'}`}
              style={{ height: `${100 / TOTAL_SLOTS}%` }}
            />
          );
        })}

        {showPreviewHere && (
          <div
            className={`absolute left-1 right-1 border-2 border-dashed rounded-lg pointer-events-none z-10 ${
              isOverlap
                ? 'border-red-500 bg-red-100/60'
                : 'border-mint-500 bg-mint-100/50'
            }`}
            style={{
              top: `${(preview!.slotIdx / TOTAL_SLOTS) * 100}%`,
              height: `${preview!.durationSlots / TOTAL_SLOTS * 100}%`,
            }}
          >
            {isOverlap && (
              <span className="absolute -top-2 left-1 text-[10px] bg-red-500 text-white px-1.5 py-0.5 rounded shadow z-20">
                ⚠ 重叠
              </span>
            )}
          </div>
        )}

        {cellReservations.map((r) => {
          const colBaseMin = setMinutes(
            setHours(startOfDay(day), DAY_START_HOUR),
            0
          ).getTime();
          const offsetMin =
            (parseISO(r.startTime).getTime() - colBaseMin) / 60000;
          const durMin = differenceInMinutes(
            parseISO(r.endTime),
            parseISO(r.startTime)
          );
          const top = Math.max(
            0,
            (offsetMin / (TOTAL_SLOTS * SLOT_MINUTES)) * 100
          );
          const height = (durMin / (TOTAL_SLOTS * SLOT_MINUTES)) * 100;
          const isOver = cellInstOverlaps.includes(r.id);
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
                isOverlapping={isOver}
                compact={height < 0.1}
                onClick={() => openDrawer(r.id)}
              />
            </div>
          );
        })}
      </DroppableCell>
    );
  }

  return (
    <DndContext
      sensors={sensors}
      collisionDetection={closestCenter}
      onDragStart={handleDragStart}
      onDragOver={handleDragOver}
      onDragEnd={handleDragEnd}
      onDragCancel={() => {
        setActiveId(null);
        setActiveReservation(null);
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
                    <p
                      className={`text-xs font-semibold ${
                        isToday(day) ? 'text-mint-700' : 'text-base-700'
                      }`}
                    >
                      {formatWeekday(day)}
                    </p>
                    <p
                      className={`text-sm font-bold ${
                        isToday(day) ? 'text-mint-600' : 'text-base-800'
                      }`}
                    >
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
              {selectedInstruments.map((inst) => {
                const cellInstOverlaps = overlapsByInst.get(inst.id) ?? [];
                return (
                  <div
                    key={inst.id}
                    className="flex border-b border-base-200 last:border-b-0 min-h-0"
                    style={{ flex: '1 1 0', minHeight: '220px' }}
                  >
                    <div className="w-28 shrink-0 border-r border-base-200 bg-gradient-to-b from-sage-50 to-mint-50 p-2 flex flex-col">
                      <p className="text-xs font-semibold text-base-800 leading-snug line-clamp-3">
                        {inst.name}
                      </p>
                      <p className="text-[10px] text-base-500 mt-1">
                        {inst.model}
                      </p>
                      {cellInstOverlaps.length > 0 && (
                        <p className="text-[10px] text-red-600 mt-1 bg-red-50 border border-red-200 px-1 py-0.5 rounded text-center">
                          ⚠ {cellInstOverlaps.length} 重叠
                        </p>
                      )}
                      <p className="text-[10px] text-base-400 mt-auto">
                        {inst.location}
                      </p>
                    </div>
                    <div className="flex-1 flex min-w-0 relative overflow-x-auto scrollbar-thin">
                      {weekDates.map((day) => renderCell(inst, day))}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </div>

      <DragOverlay dropAnimation={{ duration: 180, easing: 'cubic-bezier(0.18,0.67,0.6,1.22)' }}>
        {activeReservation && (
          <div style={{ width: '220px' }}>
            <ReservationCard
              reservation={activeReservation}
              isOverlapping={preview?.wouldOverlap ?? false}
              disableDrag
            />
          </div>
        )}
      </DragOverlay>
    </DndContext>
  );
}
