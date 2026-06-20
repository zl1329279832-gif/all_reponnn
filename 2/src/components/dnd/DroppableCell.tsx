import { useDroppable } from '@dnd-kit/core';
import type { ReactNode } from 'react';
import { useRef, useCallback } from 'react';

export interface DroppableCellMeta {
  instrumentId: string;
  dayDate: string;
}

export function encodeDroppableId(instrumentId: string, dayDate: string): string {
  return `drop__${instrumentId}__${dayDate}`;
}

export function decodeDroppableId(
  id: string | undefined | null
): DroppableCellMeta | null {
  if (!id || typeof id !== 'string' || !id.startsWith('drop__')) return null;
  const parts = id.split('__');
  if (parts.length !== 3) return null;
  return { instrumentId: parts[1], dayDate: parts[2] };
}

export interface DroppableCellHandle {
  computeSlotIndex(clientY: number, totalSlots: number): number;
}

interface Props {
  instrumentId: string;
  dayDate: string;
  className?: string;
  style?: React.CSSProperties;
  children: ReactNode;
  onSlotIndexChange?: (slotIdx: number) => void;
  /** 子元素占满容器的高度比例，用于换算 slot */
  totalSlots: number;
  registerHandle?: (ref: DroppableCellHandle | null) => void;
  activeDrop?: boolean;
}

export function DroppableCell({
  instrumentId,
  dayDate,
  className,
  style,
  children,
  onSlotIndexChange,
  totalSlots,
  registerHandle,
  activeDrop,
}: Props) {
  const id = encodeDroppableId(instrumentId, dayDate);
  const { setNodeRef, isOver } = useDroppable({
    id,
    data: { instrumentId, dayDate },
  });

  const rectRef = useRef<DOMRect | null>(null);

  const wrapperRef = useCallback(
    (el: HTMLDivElement | null) => {
      setNodeRef(el);
      if (el) {
        rectRef.current = el.getBoundingClientRect();
      } else {
        rectRef.current = null;
      }
      if (registerHandle) {
        if (el) {
          registerHandle({
            computeSlotIndex(clientY, slots) {
              const rect = el.getBoundingClientRect();
              const relY = Math.max(0, Math.min(rect.height, clientY - rect.top));
              const slotH = rect.height / slots;
              return Math.max(0, Math.min(slots - 1, Math.floor(relY / slotH)));
            },
          });
        } else {
          registerHandle(null);
        }
      }
    },
    [setNodeRef, registerHandle]
  );

  function handlePointerMove(e: React.PointerEvent<HTMLDivElement>) {
    if (!onSlotIndexChange) return;
    const el = e.currentTarget;
    const rect = el.getBoundingClientRect();
    const relY = Math.max(0, Math.min(rect.height, e.clientY - rect.top));
    const slotH = rect.height / totalSlots;
    const idx = Math.max(0, Math.min(totalSlots - 1, Math.floor(relY / slotH)));
    onSlotIndexChange(idx);
  }

  return (
    <div
      ref={wrapperRef}
      onPointerMove={handlePointerMove}
      className={`${className ?? ''} ${
        isOver || activeDrop ? 'ring-2 ring-mint-300/60 z-10 relative' : ''
      }`}
      style={style}
      data-droppable-id={id}
    >
      {children}
    </div>
  );
}
