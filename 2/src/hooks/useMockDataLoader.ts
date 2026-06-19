import { useEffect, useState } from 'react';
import { useScheduleStore } from '../store/scheduleStore';
import type { Instrument, Reservation } from '../types';

export function useMockDataLoader() {
  const setInstruments = useScheduleStore((s) => s.setInstruments);
  const setReservations = useScheduleStore((s) => s.setReservations);
  const reservations = useScheduleStore((s) => s.reservations);
  const instruments = useScheduleStore((s) => s.instruments);
  const isHydrated = useScheduleStore((s) => s.isHydrated);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const [instRes, resvRes] = await Promise.all([
          fetch('/mock/instruments.json'),
          fetch('/mock/reservations.json'),
        ]);
        if (!instRes.ok || !resvRes.ok) {
          throw new Error('加载 mock 数据失败');
        }
        const instList = (await instRes.json()) as Instrument[];
        const resvList = (await resvRes.json()) as Reservation[];
        if (cancelled) return;

        setInstruments(instList);

        if (reservations.length === 0) {
          setReservations(resvList);
        }
      } catch (e) {
        if (!cancelled) setError((e as Error).message);
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    load();
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isHydrated]);

  return { loading, error, instruments, reservations };
}
