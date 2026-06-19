import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';
import type { Instrument, Reservation, ScheduleState, ViewMode } from '../types';
import { getMondayOfWeek, hasOverlap, addWeeks, parseISO, isSameDay, addMinutes, differenceInMinutes, snapAndClampReservationToDay, setHours, setMinutes, startOfDay } from '../utils/dateUtils';

interface ScheduleStore extends ScheduleState {
  isHydrated: boolean;
  setInstruments: (list: Instrument[]) => void;
  setReservations: (list: Reservation[]) => void;
  toggleInstrument: (id: string) => void;
  selectAllInstruments: () => void;
  clearInstrumentSelection: () => void;
  setViewMode: (mode: ViewMode) => void;
  setCurrentWeekStart: (dateStr: string) => void;
  goToPrevWeek: () => void;
  goToNextWeek: () => void;
  goToCurrentWeek: () => void;
  openDrawer: (reservationId?: string) => void;
  closeDrawer: () => void;
  updateReservation: (id: string, patch: Partial<Reservation>) => { success: boolean; overlapped?: boolean };
  createReservation: (data: Omit<Reservation, 'id' | 'createdAt'>) => { success: boolean; id?: string; overlapped?: boolean };
  deleteReservation: (id: string) => void;
  moveReservationTo: (
    id: string,
    targetInstrumentId: string,
    newStartTime: string,
    newEndTime: string
  ) => { success: boolean; overlapped: boolean };
  findOverlapsOnInstrument: (instrumentId: string, date?: Date) => string[];
  getInstrumentReservations: (instrumentId: string) => Reservation[];
  markHydrated: () => void;
}

const today = new Date();
const monday = getMondayOfWeek(today);

const initialState: Omit<ScheduleState, 'instruments' | 'reservations'> = {
  selectedInstrumentIds: [],
  currentWeekStart: monday.toISOString(),
  viewMode: 'board',
  editingReservationId: null,
  drawerOpen: false,
};

export const useScheduleStore = create<ScheduleStore>()(
  persist(
    (set, get) => ({
      ...initialState,
      instruments: [],
      reservations: [],
      isHydrated: false,

      markHydrated: () => set({ isHydrated: true }),

      setInstruments: (list) => {
        const prev = get();
        const selected =
          prev.selectedInstrumentIds.length === 0 ? list.map((i) => i.id) : prev.selectedInstrumentIds;
        set({ instruments: list, selectedInstrumentIds: selected });
      },

      setReservations: (list) => set({ reservations: list }),

      toggleInstrument: (id) => {
        const { selectedInstrumentIds } = get();
        const exists = selectedInstrumentIds.includes(id);
        set({
          selectedInstrumentIds: exists
            ? selectedInstrumentIds.filter((x) => x !== id)
            : [...selectedInstrumentIds, id],
        });
      },

      selectAllInstruments: () => {
        set({ selectedInstrumentIds: get().instruments.map((i) => i.id) });
      },

      clearInstrumentSelection: () => set({ selectedInstrumentIds: [] }),

      setViewMode: (mode) => set({ viewMode: mode }),

      setCurrentWeekStart: (dateStr) => set({ currentWeekStart: dateStr }),

      goToPrevWeek: () => {
        const cur = parseISO(get().currentWeekStart);
        set({ currentWeekStart: addWeeks(cur, -1).toISOString() });
      },

      goToNextWeek: () => {
        const cur = parseISO(get().currentWeekStart);
        set({ currentWeekStart: addWeeks(cur, 1).toISOString() });
      },

      goToCurrentWeek: () => {
        set({ currentWeekStart: getMondayOfWeek(new Date()).toISOString() });
      },

      openDrawer: (reservationId) => {
        set({ drawerOpen: true, editingReservationId: reservationId ?? null });
      },

      closeDrawer: () => set({ drawerOpen: false, editingReservationId: null }),

      getInstrumentReservations: (instrumentId) =>
        get().reservations.filter((r) => r.instrumentId === instrumentId),

      updateReservation: (id, patch) => {
        const state = get();
        const target = state.reservations.find((r) => r.id === id);
        if (!target) return { success: false };
        const merged = { ...target, ...patch };
        const siblings = state.reservations.filter(
          (r) => r.instrumentId === merged.instrumentId
        );
        if (
          (patch.startTime || patch.endTime || patch.instrumentId) &&
          hasOverlap(
            { startTime: merged.startTime, endTime: merged.endTime },
            siblings,
            id
          )
        ) {
          return { success: false, overlapped: true };
        }
        set({
          reservations: state.reservations.map((r) => (r.id === id ? merged : r)),
        });
        return { success: true };
      },

      createReservation: (data) => {
        const state = get();
        const siblings = state.reservations.filter(
          (r) => r.instrumentId === data.instrumentId
        );
        if (hasOverlap({ startTime: data.startTime, endTime: data.endTime }, siblings)) {
          return { success: false, overlapped: true };
        }
        const id = `res-${Date.now()}-${Math.floor(Math.random() * 10000)}`;
        const newRes: Reservation = {
          ...data,
          id,
          createdAt: new Date().toISOString(),
        };
        set({ reservations: [...state.reservations, newRes] });
        return { success: true, id };
      },

      deleteReservation: (id) => {
        set({ reservations: get().reservations.filter((r) => r.id !== id) });
      },

      moveReservationTo: (id, targetInstrumentId, newStartTime, newEndTime) => {
        const state = get();
        const target = state.reservations.find((r) => r.id === id);
        if (!target) return { success: false, overlapped: false };

        const duration = differenceInMinutes(
          parseISO(newEndTime),
          parseISO(newStartTime)
        );
        const realDuration = duration > 0 ? duration : differenceInMinutes(
          parseISO(target.endTime),
          parseISO(target.startTime)
        );

        const dayStart = startOfDay(parseISO(newStartTime));
        const snapped = snapAndClampReservationToDay(newStartTime, realDuration, dayStart);

        const siblings = state.reservations.filter(
          (r) => r.instrumentId === targetInstrumentId
        );
        const overlap = hasOverlap(
          { startTime: snapped.startTime, endTime: snapped.endTime },
          siblings,
          id
        );
        if (overlap) {
          return { success: false, overlapped: true };
        }

        set({
          reservations: state.reservations.map((r) =>
            r.id === id
              ? {
                  ...r,
                  instrumentId: targetInstrumentId,
                  startTime: snapped.startTime,
                  endTime: snapped.endTime,
                }
              : r
          ),
        });
        return { success: true, overlapped: false };
      },

      findOverlapsOnInstrument: (instrumentId, date) => {
        const res = get()
          .reservations.filter((r) => r.instrumentId === instrumentId)
          .filter((r) => (date ? isSameDay(parseISO(r.startTime), date) : true));
        const overlapIds = new Set<string>();
        for (let i = 0; i < res.length; i++) {
          for (let j = i + 1; j < res.length; j++) {
            if (
              hasOverlap(
                { startTime: res[i].startTime, endTime: res[i].endTime },
                [res[j]]
              )
            ) {
              overlapIds.add(res[i].id);
              overlapIds.add(res[j].id);
            }
          }
        }
        return Array.from(overlapIds);
      },
    }),
    {
      name: 'lab-scheduler-state',
      storage: createJSONStorage(() => localStorage),
      partialize: (state) => ({
        reservations: state.reservations,
        selectedInstrumentIds: state.selectedInstrumentIds,
        currentWeekStart: state.currentWeekStart,
        viewMode: state.viewMode,
      }),
      onRehydrateStorage: () => (state) => {
        if (state) {
          state.markHydrated();
        }
      },
    }
  )
);
