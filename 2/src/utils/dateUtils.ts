import {
  startOfWeek,
  addWeeks,
  startOfDay,
  endOfDay,
  eachMinuteOfInterval,
  differenceInMinutes,
  format,
  parseISO,
  isSameDay,
  addMinutes,
  setHours,
  setMinutes,
  isWithinInterval,
} from 'date-fns';
import { zhCN } from 'date-fns/locale';
import type { Reservation } from '../types';

export const SLOT_MINUTES = 30;
export const DAY_START_HOUR = 8;
export const DAY_END_HOUR = 20;
export const MINUTES_PER_HOUR = 60;

export function getMondayOfWeek(date: Date = new Date()): Date {
  return startOfWeek(date, { weekStartsOn: 1 });
}

export function getWeekDates(weekStart: Date): Date[] {
  const dates: Date[] = [];
  for (let i = 0; i < 7; i++) {
    const d = new Date(weekStart);
    d.setDate(d.getDate() + i);
    dates.push(d);
  }
  return dates;
}

export function getDayTimeSlots(baseDate: Date): Date[] {
  const start = setMinutes(setHours(startOfDay(baseDate), DAY_START_HOUR), 0);
  const end = setMinutes(setHours(startOfDay(baseDate), DAY_END_HOUR), 0);
  return eachMinuteOfInterval(
    { start, end },
    { step: SLOT_MINUTES }
  );
}

export function slotToMinutesOffset(date: Date): number {
  const base = setMinutes(setHours(startOfDay(date), DAY_START_HOUR), 0);
  return Math.max(0, differenceInMinutes(date, base));
}

export function minutesToDurationLabel(minutes: number): string {
  const h = Math.floor(minutes / MINUTES_PER_HOUR);
  const m = minutes % MINUTES_PER_HOUR;
  if (h === 0) return `${m}分钟`;
  if (m === 0) return `${h}小时`;
  return `${h}小时${m}分`;
}

export function formatDateLabel(date: Date): string {
  return format(date, 'MM月dd日 EEEE', { locale: zhCN });
}

export function formatShortDate(date: Date): string {
  return format(date, 'MM/dd', { locale: zhCN });
}

export function formatWeekday(date: Date): string {
  return format(date, 'EEEE', { locale: zhCN });
}

export function formatTime(date: Date | string): string {
  const d = typeof date === 'string' ? parseISO(date) : date;
  return format(d, 'HH:mm');
}

export function formatDateTimeRange(start: string, end: string): string {
  const s = parseISO(start);
  const e = parseISO(end);
  if (isSameDay(s, e)) {
    return `${format(s, 'MM/dd HH:mm', { locale: zhCN })} ~ ${format(e, 'HH:mm')}`;
  }
  return `${format(s, 'MM/dd HH:mm', { locale: zhCN })} ~ ${format(e, 'MM/dd HH:mm', { locale: zhCN })}`;
}

export function snapToSlot(date: Date): Date {
  const minutes = date.getMinutes();
  const snapped = Math.round(minutes / SLOT_MINUTES) * SLOT_MINUTES;
  if (snapped >= MINUTES_PER_HOUR) {
    return setMinutes(setHours(date, date.getHours() + 1), snapped - MINUTES_PER_HOUR);
  }
  return setMinutes(date, snapped);
}

export function hasOverlap(
  target: Pick<Reservation, 'startTime' | 'endTime'>,
  others: Pick<Reservation, 'id' | 'startTime' | 'endTime'>[],
  ignoreId?: string
): boolean {
  const tStart = parseISO(target.startTime).getTime();
  const tEnd = parseISO(target.endTime).getTime();
  for (const o of others) {
    if (ignoreId && o.id === ignoreId) continue;
    const oStart = parseISO(o.startTime).getTime();
    const oEnd = parseISO(o.endTime).getTime();
    if (tStart < oEnd && oStart < tEnd) {
      return true;
    }
  }
  return false;
}

export function snapAndClampReservationToDay(
  startTimeStr: string,
  durationMin: number,
  targetDay: Date
): { startTime: string; endTime: string } {
  let start = snapToSlot(parseISO(startTimeStr));
  if (!isSameDay(start, targetDay)) {
    start = setMinutes(setHours(startOfDay(targetDay), DAY_START_HOUR), 0);
  }
  const minStart = setMinutes(setHours(startOfDay(targetDay), DAY_START_HOUR), 0);
  const maxEnd = setMinutes(setHours(startOfDay(targetDay), DAY_END_HOUR), 0);
  if (start < minStart) start = minStart;
  let end = addMinutes(start, durationMin);
  if (end > maxEnd) {
    end = maxEnd;
    start = addMinutes(end, -durationMin);
    if (start < minStart) start = minStart;
  }
  return {
    startTime: start.toISOString(),
    endTime: end.toISOString(),
  };
}

export function isToday(date: Date): boolean {
  return isSameDay(date, new Date());
}

export {
  addWeeks,
  startOfDay,
  endOfDay,
  differenceInMinutes,
  format,
  parseISO,
  isSameDay,
  addMinutes,
  setHours,
  setMinutes,
  isWithinInterval,
  isWithinInterval as isTimeWithin,
};
