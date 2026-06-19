import { useDraggable } from '@dnd-kit/core';
import { CSS } from '@dnd-kit/utilities';
import type { Reservation } from '../../types';
import { formatTime, differenceInMinutes, parseISO, minutesToDurationLabel } from '../../utils/dateUtils';

interface Props {
  reservation: Reservation;
  isOverlapping?: boolean;
  compact?: boolean;
  onClick?: () => void;
  style?: React.CSSProperties;
  disableDrag?: boolean;
}

export function ReservationCard({
  reservation,
  isOverlapping = false,
  compact = false,
  onClick,
  style,
  disableDrag = false,
}: Props) {
  const { attributes, listeners, setNodeRef, transform, isDragging } = useDraggable({
    id: reservation.id,
    disabled: disableDrag,
    data: { reservation },
  });

  const dragStyle: React.CSSProperties = disableDrag
    ? {}
    : {
        transform: CSS.Translate.toString(transform),
      };

  const duration = differenceInMinutes(
    parseISO(reservation.endTime),
    parseISO(reservation.startTime)
  );

  const baseCls = isOverlapping
    ? 'border-red-400 bg-red-50 text-red-900 ring-2 ring-red-300'
    : 'border-mint-200 bg-gradient-to-br from-white to-mint-50 text-base-800 hover:shadow-md';

  return (
    <div
      ref={setNodeRef}
      style={{ ...style, ...dragStyle }}
      onClick={onClick}
      {...(disableDrag ? {} : { ...attributes, ...listeners })}
      className={`
        group relative w-full rounded-lg border text-left p-2 shadow-sm
        transition-all duration-150 cursor-grab active:cursor-grabbing select-none
        ${baseCls}
        ${isDragging ? 'opacity-60 z-50 shadow-xl ring-2 ring-mint-400 scale-[1.02]' : ''}
        ${compact ? 'text-xs' : 'text-sm'}
      `}
    >
      <div className={`flex items-start justify-between gap-1 ${compact ? 'mb-0.5' : 'mb-1'}`}>
        <p
          className={`font-semibold truncate flex-1 ${
            isOverlapping ? 'text-red-800' : 'text-base-900'
          } ${compact ? 'text-[11px] leading-tight' : ''}`}
        >
          {reservation.experimentName}
        </p>
        {isOverlapping && (
          <span className="shrink-0 text-[10px] bg-red-500 text-white px-1.5 py-0.5 rounded-full">
            ⚠ 重叠
          </span>
        )}
      </div>

      <div className={`flex items-center gap-1 text-[11px] ${isOverlapping ? 'text-red-700' : 'text-base-600'}`}>
        <span className="whitespace-nowrap">
          {formatTime(reservation.startTime)}–{formatTime(reservation.endTime)}
        </span>
        {!compact && (
          <>
            <span className="opacity-40">·</span>
            <span>{minutesToDurationLabel(duration)}</span>
          </>
        )}
      </div>

      {!compact && (
        <>
          <div className="mt-1.5 flex items-center justify-between text-[11px]">
            <span className="flex items-center gap-1 text-base-700">
              <span className="opacity-70">👤</span>
              <span className="truncate">{reservation.owner}</span>
            </span>
            <span
              className={`px-1.5 py-0.5 rounded ${
                isOverlapping
                  ? 'bg-red-100 text-red-700'
                  : 'bg-mint-100 text-mint-700'
              }`}
            >
              {reservation.sampleCount}样
            </span>
          </div>
          {reservation.remarks && (
            <p className="mt-1 text-[11px] text-base-500 line-clamp-2 leading-snug">
              {reservation.remarks}
            </p>
          )}
        </>
      )}
    </div>
  );
}
