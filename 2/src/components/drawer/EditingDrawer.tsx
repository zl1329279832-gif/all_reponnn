import { useEffect, useMemo, useState } from 'react';
import { useScheduleStore } from '../../store/scheduleStore';
import type { Reservation } from '../../types';
import {
  formatDateTimeRange,
  formatTime,
  parseISO,
  differenceInMinutes,
  minutesToDurationLabel,
  addMinutes,
  isSameDay,
  DAY_START_HOUR,
  DAY_END_HOUR,
  SLOT_MINUTES,
  setHours,
  setMinutes,
  startOfDay,
  snapAndClampReservationToDay,
} from '../../utils/dateUtils';
import { hasOverlap } from '../../utils/dateUtils';

type Errors = Partial<Record<'experimentName' | 'owner' | 'sampleCount' | 'time', string>>;

export function EditingDrawer() {
  const open = useScheduleStore((s) => s.drawerOpen);
  const editingId = useScheduleStore((s) => s.editingReservationId);
  const reservations = useScheduleStore((s) => s.reservations);
  const instruments = useScheduleStore((s) => s.instruments);
  const close = useScheduleStore((s) => s.closeDrawer);
  const updateReservation = useScheduleStore((s) => s.updateReservation);
  const createReservation = useScheduleStore((s) => s.createReservation);
  const deleteReservation = useScheduleStore((s) => s.deleteReservation);
  const currentWeekStart = useScheduleStore((s) => s.currentWeekStart);

  const baseReservation = useMemo<Reservation | null>(
    () => (editingId ? reservations.find((r) => r.id === editingId) ?? null : null),
    [editingId, reservations]
  );

  const isCreating = !baseReservation && open;

  const [experimentName, setExperimentName] = useState('');
  const [owner, setOwner] = useState('');
  const [sampleCount, setSampleCount] = useState<number>(1);
  const [remarks, setRemarks] = useState('');
  const [instrumentId, setInstrumentId] = useState('');
  const [startDate, setStartDate] = useState('');
  const [startTime, setStartTime] = useState('');
  const [endTime, setEndTime] = useState('');
  const [errors, setErrors] = useState<Errors>({});
  const [overlapWarning, setOverlapWarning] = useState(false);
  const [successMsg, setSuccessMsg] = useState('');

  useEffect(() => {
    if (!open) return;
    if (baseReservation) {
      const s = parseISO(baseReservation.startTime);
      const e = parseISO(baseReservation.endTime);
      setExperimentName(baseReservation.experimentName);
      setOwner(baseReservation.owner);
      setSampleCount(baseReservation.sampleCount);
      setRemarks(baseReservation.remarks ?? '');
      setInstrumentId(baseReservation.instrumentId);
      setStartDate(formatDateOnly(s));
      setStartTime(formatTime(s));
      setEndTime(formatTime(e));
    } else {
      const base = parseISO(currentWeekStart);
      setExperimentName('');
      setOwner('');
      setSampleCount(1);
      setRemarks('');
      setInstrumentId(instruments[0]?.id ?? '');
      setStartDate(formatDateOnly(base));
      setStartTime('09:00');
      setEndTime('10:00');
    }
    setErrors({});
    setOverlapWarning(false);
    setSuccessMsg('');
  }, [open, baseReservation, currentWeekStart, instruments]);

  function formatDateOnly(d: Date): string {
    const y = d.getFullYear();
    const m = String(d.getMonth() + 1).padStart(2, '0');
    const day = String(d.getDate()).padStart(2, '0');
    return `${y}-${m}-${day}`;
  }

  function parseDateTime(dateStr: string, timeStr: string): Date {
    const [h, m] = timeStr.split(':').map(Number);
    const [y, mo, d] = dateStr.split('-').map(Number);
    return new Date(y, mo - 1, d, h, m, 0);
  }

  function validate(): { ok: boolean; startTime?: Date; endTime?: Date } {
    const nextErrors: Errors = {};
    if (!experimentName.trim()) nextErrors.experimentName = '请输入实验名称';
    if (!owner.trim()) nextErrors.owner = '请输入负责人姓名';
    if (!sampleCount || sampleCount <= 0) nextErrors.sampleCount = '样本数需大于 0';
    if (!startDate || !startTime || !endTime) nextErrors.time = '请选择开始与结束时间';

    let s: Date | undefined;
    let e: Date | undefined;
    if (startDate && startTime && endTime) {
      s = parseDateTime(startDate, startTime);
      e = parseDateTime(startDate, endTime);
      if (!isSameDay(s, e) || e <= s) {
        nextErrors.time = '结束时间必须晚于开始时间，且需在同一天内';
      } else {
        const minStart = setHours(setMinutes(startOfDay(s), 0), DAY_START_HOUR);
        const maxEnd = setHours(setMinutes(startOfDay(s), 0), DAY_END_HOUR);
        if (s < minStart || e > maxEnd) {
          nextErrors.time = `预约时段须在 ${String(DAY_START_HOUR).padStart(
            2,
            '0'
          )}:00 ~ ${String(DAY_END_HOUR).padStart(2, '0')}:00 内`;
        }
      }
    }
    setErrors(nextErrors);
    if (Object.keys(nextErrors).length > 0) return { ok: false };
    return { ok: true, startTime: s, endTime: e };
  }

  function handleSave() {
    const v = validate();
    if (!v.ok || !v.startTime || !v.endTime) return;

    const day = startOfDay(v.startTime);
    const dur = differenceInMinutes(v.endTime, v.startTime);
    const snapped = snapAndClampReservationToDay(v.startTime.toISOString(), dur, day);

    const siblings = reservations.filter(
      (r) => r.instrumentId === instrumentId
    );
    const isOverlap = hasOverlap(
      { startTime: snapped.startTime, endTime: snapped.endTime },
      siblings,
      baseReservation?.id
    );
    if (isOverlap) {
      setOverlapWarning(true);
      return;
    }
    setOverlapWarning(false);

    const payload = {
      experimentName: experimentName.trim(),
      owner: owner.trim(),
      sampleCount: Math.max(1, Math.floor(sampleCount)),
      remarks: remarks.trim(),
      instrumentId,
      startTime: snapped.startTime,
      endTime: snapped.endTime,
    };

    if (baseReservation) {
      const r = updateReservation(baseReservation.id, payload);
      if (r.success) {
        setSuccessMsg('保存成功，已同步到本地');
        setTimeout(() => setSuccessMsg(''), 1500);
      } else if (r.overlapped) {
        setOverlapWarning(true);
      }
    } else {
      const r = createReservation(payload);
      if (r.success) {
        setSuccessMsg('新建预约成功，已同步到本地');
        setTimeout(() => {
          setSuccessMsg('');
          close();
        }, 1000);
      } else if (r.overlapped) {
        setOverlapWarning(true);
      }
    }
  }

  function handleDelete() {
    if (!baseReservation) return;
    if (window.confirm(`确认删除「${baseReservation.experimentName}」预约吗？`)) {
      deleteReservation(baseReservation.id);
      close();
    }
  }

  const instrument = instruments.find((i) => i.id === instrumentId);

  return (
    <>
      <div
        className={`fixed inset-0 bg-base-900/30 backdrop-blur-sm z-40 transition-opacity duration-200 ${
          open ? 'opacity-100 pointer-events-auto' : 'opacity-0 pointer-events-none'
        }`}
        onClick={close}
      />
      <aside
        className={`fixed top-0 right-0 h-full w-full sm:w-[440px] bg-white shadow-2xl z-50 flex flex-col transition-transform duration-300 border-l border-base-200 ${
          open ? 'translate-x-0' : 'translate-x-full'
        }`}
      >
        <header className="px-5 py-4 border-b border-base-200 bg-gradient-to-r from-sage-50 to-mint-50 flex items-start gap-3 shrink-0">
          <div className="w-10 h-10 rounded-lg bg-white shadow-sm border border-base-100 flex items-center justify-center text-lg shrink-0">
            {isCreating ? '➕' : '📝'}
          </div>
          <div className="flex-1 min-w-0">
            <h3 className="text-lg font-bold text-base-900">
              {isCreating ? '新建预约' : '编辑预约'}
            </h3>
            <p className="text-xs text-base-500 mt-0.5">
              {isCreating
                ? '填写实验信息创建新的仪器预约'
                : `预约 ID：${baseReservation?.id ?? '-'}`}
            </p>
          </div>
          <button
            onClick={close}
            className="w-8 h-8 rounded-md text-base-500 hover:bg-white hover:shadow-sm hover:text-base-800 transition flex items-center justify-center"
          >
            ✕
          </button>
        </header>

        <div className="flex-1 overflow-y-auto scrollbar-thin px-5 py-4 space-y-5">
          {baseReservation && (
            <div className="p-3 rounded-lg border border-base-200 bg-base-50 text-sm space-y-1.5">
              <div className="flex items-center justify-between">
                <span className="text-xs text-base-500">仪器</span>
                <span className="font-medium text-base-800">
                  {instrument?.name ?? '-'}
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-xs text-base-500">时段</span>
                <span className="font-medium text-mint-700">
                  {formatDateTimeRange(baseReservation.startTime, baseReservation.endTime)}
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-xs text-base-500">时长</span>
                <span className="font-medium text-base-700">
                  {minutesToDurationLabel(
                    differenceInMinutes(
                      parseISO(baseReservation.endTime),
                      parseISO(baseReservation.startTime)
                    )
                  )}
                </span>
              </div>
            </div>
          )}

          <div>
            <label className="block text-xs font-semibold text-base-700 mb-1.5">
              预约仪器 <span className="text-red-500">*</span>
            </label>
            <select
              value={instrumentId}
              onChange={(e) => setInstrumentId(e.target.value)}
              className="w-full text-sm px-3 py-2 rounded-lg border border-base-200 bg-white focus:outline-none focus:ring-2 focus:ring-mint-400 transition"
            >
              {instruments.map((i) => (
                <option key={i.id} value={i.id}>
                  {i.name} · {i.model}（{i.location}）
                </option>
              ))}
            </select>
          </div>

          <div className="grid grid-cols-3 gap-3">
            <div className="col-span-3 sm:col-span-1">
              <label className="block text-xs font-semibold text-base-700 mb-1.5">
                日期
              </label>
              <input
                type="date"
                value={startDate}
                onChange={(e) => setStartDate(e.target.value)}
                className="w-full text-sm px-3 py-2 rounded-lg border border-base-200 focus:outline-none focus:ring-2 focus:ring-mint-400 transition"
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-base-700 mb-1.5">
                开始时间
              </label>
              <input
                type="time"
                value={startTime}
                step={SLOT_MINUTES * 60}
                min={`${String(DAY_START_HOUR).padStart(2, '0')}:00`}
                max={`${String(DAY_END_HOUR).padStart(2, '0')}:00`}
                onChange={(e) => setStartTime(e.target.value)}
                className="w-full text-sm px-3 py-2 rounded-lg border border-base-200 focus:outline-none focus:ring-2 focus:ring-mint-400 transition"
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-base-700 mb-1.5">
                结束时间
              </label>
              <input
                type="time"
                value={endTime}
                step={SLOT_MINUTES * 60}
                min={`${String(DAY_START_HOUR).padStart(2, '0')}:00`}
                max={`${String(DAY_END_HOUR).padStart(2, '0')}:00`}
                onChange={(e) => setEndTime(e.target.value)}
                className="w-full text-sm px-3 py-2 rounded-lg border border-base-200 focus:outline-none focus:ring-2 focus:ring-mint-400 transition"
              />
            </div>
            {(errors.time || overlapWarning) && (
              <div className="col-span-3">
                {errors.time && (
                  <p className="text-xs text-red-600">{errors.time}</p>
                )}
                {overlapWarning && (
                  <p className="text-xs text-red-600 p-2 rounded bg-red-50 border border-red-200">
                    ⚠ 该仪器在所选时段已有其他预约，时间段重叠被拦截。请更换时段或仪器。
                  </p>
                )}
              </div>
            )}
          </div>

          <div>
            <label className="block text-xs font-semibold text-base-700 mb-1.5">
              实验名称 <span className="text-red-500">*</span>
            </label>
            <input
              type="text"
              value={experimentName}
              onChange={(e) => setExperimentName(e.target.value)}
              placeholder="例如：蛋白质浓度测定"
              className={`w-full text-sm px-3 py-2 rounded-lg border focus:outline-none focus:ring-2 focus:ring-mint-400 transition ${
                errors.experimentName ? 'border-red-400 bg-red-50' : 'border-base-200'
              }`}
            />
            {errors.experimentName && (
              <p className="mt-1 text-xs text-red-600">{errors.experimentName}</p>
            )}
          </div>

          <div className="grid grid-cols-3 gap-3">
            <div className="col-span-2">
              <label className="block text-xs font-semibold text-base-700 mb-1.5">
                负责人 <span className="text-red-500">*</span>
              </label>
              <input
                type="text"
                value={owner}
                onChange={(e) => setOwner(e.target.value)}
                placeholder="姓名"
                className={`w-full text-sm px-3 py-2 rounded-lg border focus:outline-none focus:ring-2 focus:ring-mint-400 transition ${
                  errors.owner ? 'border-red-400 bg-red-50' : 'border-base-200'
                }`}
              />
              {errors.owner && (
                <p className="mt-1 text-xs text-red-600">{errors.owner}</p>
              )}
            </div>
            <div>
              <label className="block text-xs font-semibold text-base-700 mb-1.5">
                样本数 <span className="text-red-500">*</span>
              </label>
              <input
                type="number"
                min={1}
                value={sampleCount}
                onChange={(e) => setSampleCount(Number(e.target.value))}
                className={`w-full text-sm px-3 py-2 rounded-lg border focus:outline-none focus:ring-2 focus:ring-mint-400 transition ${
                  errors.sampleCount ? 'border-red-400 bg-red-50' : 'border-base-200'
                }`}
              />
              {errors.sampleCount && (
                <p className="mt-1 text-xs text-red-600">{errors.sampleCount}</p>
              )}
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-base-700 mb-1.5">
              备注
            </label>
            <textarea
              value={remarks}
              onChange={(e) => setRemarks(e.target.value)}
              rows={4}
              placeholder="实验条件、特殊要求等"
              className="w-full text-sm px-3 py-2 rounded-lg border border-base-200 focus:outline-none focus:ring-2 focus:ring-mint-400 transition resize-none"
            />
          </div>
        </div>

        <footer className="px-5 py-3 border-t border-base-200 bg-base-50/80 flex items-center gap-2 shrink-0">
          {successMsg && (
            <span className="text-xs text-mint-700 bg-mint-50 border border-mint-200 px-2 py-1 rounded-md mr-auto">
              ✓ {successMsg}
            </span>
          )}
          {baseReservation && (
            <button
              onClick={handleDelete}
              className="px-3 py-2 rounded-md text-sm text-red-700 bg-red-50 border border-red-200 hover:bg-red-100 transition"
            >
              删除
            </button>
          )}
          {!successMsg && <div className="flex-1" />}
          <button
            onClick={close}
            className="px-4 py-2 rounded-md text-sm text-base-700 bg-white border border-base-200 hover:bg-base-100 transition"
          >
            取消
          </button>
          <button
            onClick={handleSave}
            className="px-4 py-2 rounded-md text-sm font-medium text-white bg-gradient-to-r from-mint-500 to-sage-500 hover:from-mint-600 hover:to-sage-600 shadow-sm transition"
          >
            保存
          </button>
        </footer>
      </aside>
    </>
  );
}
