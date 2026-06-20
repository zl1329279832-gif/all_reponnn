import { useMemo, useRef, useState, useCallback } from 'react';
import {
  DndContext,
  DragOverlay,
  closestCenter,
  PointerSensor,
  useSensor,
  useSensors,
  type DragEndEvent,
  type DragStartEvent,
  type DragOverEvent,
} from '@dnd-kit/core';
import { useScheduleStore } from '../../store/scheduleStore';
import { ReservationCard } from '../common/ReservationCard';
import {
  DroppableCell,
  decodeDroppableId,
  type DroppableCellHandle,
} from '../dnd/DroppableCell';
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
  addMinutes,
  startOfDay,
  setHours,
  setMinutes,
  hasOverlap,
} from '../../utils/dateUtils';
import { toast } from '../../store/toastStore';

const TOTAL_SLOTS = ((DAY_END_HOUR - DAY_START_HOUR) * 60) / SLOT_MINUTES;

interface DropTarget {
  instrumentId: string;
  day: Date;
  slotIdx: number;
  wouldOverlap: boolean;
  durationSlots: number;
}

function InstrumentDayColumn({
  instrument,
  day,
  reservations,
  overlappedIds,
  onCardClick,
  onSlotIndexChange,
  registerHandle,
  activeDrop,
  preview,
}: {
  instrument: Instrument;
  day: Date;
  reservations: Reservation[];
  overlappedIds: string[];
  onCardClick: (id: string) => void;
  onSlotIndexChange: (slotIdx: number) => void;
  registerHandle: (ref: DroppableCellHandle | null) => void;
  activeDrop: boolean;
  preview: DropTarget | null;
}) {
  const slots = useMemo(
    () => Array.from({ length: TOTAL_SLOTS }, (_, i) => i),
    []
  );

  const dayStr = formatDateOnlyISO(day);
  const showPreviewOnThisCell =
    preview &&
    preview.instrumentId === instrument.id &&
    formatDateOnlyISO(preview.day) === dayStr;
  const isOverlap = showPreviewOnThisCell && preview!.wouldOverlap;

  return (
    <div className="relative flex flex-col h-full border-l border-base-200 first:border-l-0 min-w-[220px]">
      <div className="px-2 py-2 bg-base-50 border-b border-base-200 text-center shrink-0">
        <p className={`text-[11px] ${isToday(day) ? 'text-mint-600 font-bold' : 'text-base-500'}`}>
          {formatDateLabel(day)}
          {isToday(day) && (
            <span className="ml-1 inline-block w-1.5 h-1.5 rounded-full bg-mint-500 align-middle" />
          )}
        </p>
      </div>

      <DroppableCell
        instrumentId={instrument.id}
        dayDate={dayStr}
        totalSlots={TOTAL_SLOTS}
        onSlotIndexChange={onSlotIndexChange}
        registerHandle={registerHandle}
        activeDrop={activeDrop}
        className="relative flex-1 overflow-hidden bg-white"
      >
        {slots.map((idx) => {
          const isHour = idx % 2 === 0;
          return (
            <div
              key={idx}
              className={`border-b ${isHour ? 'border-base-100' : 'border-base-50'}`}
              style={{ height: `${100 / TOTAL_SLOTS}%` }}
            />
          );
        })}

        {showPreviewOnThisCell && (
          <div
            className={`absolute left-1 right-1 border-2 border-dashed rounded-lg pointer-events-none ${
              isOverlap
                ? 'border-red-500 bg-red-100/50'
                : 'border-mint-500 bg-mint-100/40'
            }`}
            style={{
              top: `${(preview!.slotIdx / TOTAL_SLOTS) * 100}%`,
              height: `${(preview!.durationSlots ?? 2) / TOTAL_SLOTS * 100}%`,
            }}
          >
            {isOverlap && (
              <span className="absolute -top-2 left-1 text-[10px] bg-red-500 text-white px-1.5 py-0.5 rounded shadow">
                ⚠ 重叠
              </span>
            )}
          </div>
        )}

        {reservations.map((r) => {
          const rStart = parseISO(r.startTime);
          if (!isSameDay(rStart, day)) return null;
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
          const isOver = overlappedIds.includes(r.id);
          return (
            <div
              key={r.id}
              className="absolute left-1 right-1"
              style={{
                top: `${top}%`,
                height: `${height}%`,
                minHeight: '32px',
              }}
            >
              <ReservationCard
                reservation={r}
                isOverlapping={isOver}
                compact={height < 0.08}
                onClick={() => onCardClick(r.id)}
              />
            </div>
          );
        })}
      </DroppableCell>
    </div>
  );
}

function formatDateOnlyISO(d: Date): string {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  return `${y}-${m}-${day}`;
}

interface DropTargetWithDuration extends DropTarget {
  durationSlots: number;
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
  const [activeReservation, setActiveReservation] =
    useState<Reservation | null>(null);
  const [preview, setPreview] = useState<DropTargetWithDuration | null>(null);

  const slotReports = useRef<
    Map<string, { clientY: number; slotIdx: number }>
  >(new Map());
  const cellHandles = useRef<Map<string, DroppableCellHandle>>(new Map());
  const globalPointerY = useRef<number>(0);
  const globalPointerX = useRef<number>(0);
  const pointerUnbind = useRef<(() => void) | null>(null);
  const currentOverId = useRef<string | null>(null);
  const previewRef = useRef<DropTargetWithDuration | null>(null);
  const activeReservationRef = useRef<Reservation | null>(null);

  const pointerSensor = useSensor(PointerSensor, {
    activationConstraint: { distance: 5 },
  });
  const sensors = useSensors(pointerSensor);

  const selectedInstruments = useMemo(() => {
    const base =
      selectedIds.length > 0
        ? instruments.filter((i) => selectedIds.includes(i.id))
        : instruments;
    return base;
  }, [instruments, selectedIds]);

  const durationSlots = useMemo(() => {
    if (!activeReservation) return 2;
    const mins = differenceInMinutes(
      parseISO(activeReservation.endTime),
      parseISO(activeReservation.startTime)
    );
    return Math.max(1, Math.round(mins / SLOT_MINUTES));
  }, [activeReservation]);

  const computeSlotIdx = useCallback((droppableId: string, clientY: number): number => {
    const handle = cellHandles.current.get(droppableId);
    if (handle) return handle.computeSlotIndex(clientY, TOTAL_SLOTS);
    const last = slotReports.current.get(droppableId);
    if (last) return last.slotIdx;
    return 0;
  }, []);

  const findDroppableByPoint = useCallback((clientX: number, clientY: number): string | null => {
    for (const [id, handle] of cellHandles.current) {
      if (handle.containsPoint(clientX, clientY)) {
        return id;
      }
    }
    return null;
  }, []);

  const computeIfOverlapByRef = useCallback(
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

  const updatePreviewForDrop = useCallback((droppableId: string, clientY: number) => {
    const r = activeReservationRef.current;
    if (!r) return;
    const meta = decodeDroppableId(droppableId);
    if (!meta) return;

    const slotIdx = computeSlotIdx(droppableId, clientY);
    const day = parseISO(`${meta.dayDate}T00:00:00`);
    const base = setMinutes(setHours(startOfDay(day), DAY_START_HOUR), 0);
    const newStart = addMinutes(base, slotIdx * SLOT_MINUTES);
    const durMin = differenceInMinutes(
      parseISO(r.endTime),
      parseISO(r.startTime)
    );
    let newEnd = addMinutes(newStart, durMin);
    const maxEnd = setMinutes(setHours(startOfDay(day), DAY_END_HOUR), 0);
    if (newEnd > maxEnd) {
      newEnd = maxEnd;
    }
    const wouldOverlap = computeIfOverlapByRef({
      reservationId: r.id,
      instrumentId: meta.instrumentId,
      startTimeISO: newStart.toISOString(),
      endTimeISO: newEnd.toISOString(),
    });
    const next: DropTargetWithDuration = {
      instrumentId: meta.instrumentId,
      day,
      slotIdx,
      wouldOverlap,
      durationSlots: Math.max(1, Math.round(durMin / SLOT_MINUTES)),
    };
    previewRef.current = next;
    setPreview(next);
  }, [computeSlotIdx, computeIfOverlapByRef]);

  function installGlobalPointerListener() {
    const onMove = (e: PointerEvent) => {
      globalPointerY.current = e.clientY;
      globalPointerX.current = e.clientX;
      if (!activeReservationRef.current) return;
      if (!currentOverId.current) {
        const found = findDroppableByPoint(e.clientX, e.clientY);
        if (found) {
          currentOverId.current = found;
        }
      }
      if (currentOverId.current && activeReservationRef.current) {
        updatePreviewForDrop(currentOverId.current, e.clientY);
      }
    };
    window.addEventListener('pointermove', onMove, true);
    pointerUnbind.current = () => {
      window.removeEventListener('pointermove', onMove, true);
      pointerUnbind.current = null;
    };
  }

  function uninstallGlobalPointerListener() {
    if (pointerUnbind.current) {
      pointerUnbind.current();
    }
  }

  function handleDragStart(e: DragStartEvent) {
    const id = String(e.active.id);
    const r = allReservations.find((x) => x.id === id);
    slotReports.current.clear();
    currentOverId.current = null;
    previewRef.current = null;
    activeReservationRef.current = r ?? null;
    const pev = e.activatorEvent as PointerEvent | undefined;
    if (pev) {
      globalPointerY.current = pev.clientY;
      globalPointerX.current = pev.clientX;
      const initialDrop = findDroppableByPoint(pev.clientX, pev.clientY);
      if (initialDrop) {
        currentOverId.current = initialDrop;
      }
    }
    installGlobalPointerListener();
    setActiveId(id);
    setActiveReservation(r ?? null);
  }

  function handleDragOver(e: DragOverEvent) {
    if (!activeReservationRef.current) return;
    const over = e.over;
    if (!over) {
      currentOverId.current = null;
      previewRef.current = null;
      setPreview(null);
      return;
    }
    const dropId = String(over.id);
    const meta = decodeDroppableId(dropId);
    if (!meta) return;

    currentOverId.current = dropId;
    updatePreviewForDrop(dropId, globalPointerY.current);
  }

  function handleDragEnd(e: DragEndEvent) {
    const finalY = globalPointerY.current;
    const finalX = globalPointerX.current;
    let finalOverId = currentOverId.current;
    uninstallGlobalPointerListener();
    currentOverId.current = null;
    previewRef.current = null;
    activeReservationRef.current = null;

    const resId = String(e.active.id);
    const reservation = allReservations.find((r) => r.id === resId);

    setActiveId(null);
    setActiveReservation(null);
    setPreview(null);

    if (!reservation) return;
    if (!finalOverId) {
      finalOverId = findDroppableByPoint(finalX, finalY);
    }
    if (!finalOverId) {
      toast('已取消拖放', 'info', 1400);
      return;
    }
    const meta = decodeDroppableId(finalOverId);
    if (!meta) {
      toast('无效的拖放目标', 'warning');
      return;
    }

    const slotIdx = computeSlotIdx(finalOverId, finalY);

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

  function renderTimeAxis() {
    const slots = [];
    for (let h = DAY_START_HOUR; h < DAY_END_HOUR; h++) {
      slots.push(
        <div
          key={h}
          className="border-b border-base-200 text-[10px] text-base-500 text-right pr-2 pt-0.5"
          style={{
            height: `${
              ((60 / SLOT_MINUTES) * 2) / TOTAL_SLOTS * 100
            }%`,
          }}
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
      collisionDetection={closestCenter}
      onDragStart={handleDragStart}
      onDragOver={handleDragOver}
      onDragEnd={handleDragEnd}
      onDragCancel={() => {
        uninstallGlobalPointerListener();
        setActiveId(null);
        setActiveReservation(null);
        setPreview(null);
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
                  style={{ flex: '1 1 0', minHeight: '280px' }}
                >
                  <div className="flex items-center px-4 py-2 border-b border-base-100 bg-gradient-to-r from-sage-50 to-mint-50 shrink-0">
                    <div className="flex items-center gap-2 min-w-0">
                      <span className="w-2 h-2 rounded-full bg-mint-500 shrink-0" />
                      <h3 className="font-semibold text-sm text-base-800 truncate">
                        {inst.name}
                      </h3>
                      <span className="text-[11px] text-base-500 shrink-0">
                        {inst.model}
                      </span>
                      <span className="text-[11px] text-base-400 shrink-0">
                        · {inst.location}
                      </span>
                    </div>
                    <div className="ml-auto flex items-center gap-3 text-[11px] text-base-500 shrink-0">
                      {overlappedIdsAll.length > 0 && (
                        <span className="text-red-600 bg-red-50 border border-red-200 px-1.5 py-0.5 rounded">
                          ⚠ {overlappedIdsAll.length} 条重叠
                        </span>
                      )}
                      <span>本周预约 {weekReservations.length}</span>
                    </div>
                  </div>
                  <div className="flex flex-1 min-h-0">
                    <div className="w-12 shrink-0 border-r border-base-200 bg-base-50/60 pt-10">
                      {renderTimeAxis()}
                    </div>
                    <div className="flex-1 flex min-w-0 overflow-x-auto scrollbar-thin">
                      {weekDates.map((day) => {
                        const dateKey = formatDateOnlyISO(day);
                        const dropId = `drop__${inst.id}__${dateKey}`;
                        const activeDrop =
                          preview?.instrumentId === inst.id &&
                          formatDateOnlyISO(preview.day) === dateKey;
                        return (
                          <InstrumentDayColumn
                            key={`${inst.id}-${dateKey}`}
                            instrument={inst}
                            day={day}
                            reservations={weekReservations.filter((r) =>
                              isSameDay(parseISO(r.startTime), day)
                            )}
                            overlappedIds={overlappedIdsAll}
                            onCardClick={(id) => openDrawer(id)}
                            onSlotIndexChange={(idx) => {
                              slotReports.current.set(dropId, {
                                clientY: 0,
                                slotIdx: idx,
                              });
                            }}
                            registerHandle={(h) => {
                              if (h) cellHandles.current.set(dropId, h);
                              else cellHandles.current.delete(dropId);
                            }}
                            activeDrop={activeDrop}
                            preview={preview}
                          />
                        );
                      })}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      <DragOverlay dropAnimation={{ duration: 180, easing: 'cubic-bezier(0.18,0.67,0.6,1.22)' }}>
        {activeReservation && (
          <div style={{ width: '240px' }}>
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
