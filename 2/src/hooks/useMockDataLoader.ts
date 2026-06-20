import { useEffect, useState } from 'react';
import { useScheduleStore } from '../store/scheduleStore';
import type { Instrument, Reservation } from '../types';

const MOCK_VERSION = 2;
const VERSION_KEY = 'lab-scheduler-mock-version';
const DEMO_RESERVATION_IDS = ['res-017', 'res-018'];

export function useMockDataLoader() {
  const setInstruments = useScheduleStore((s) => s.setInstruments);
  const setReservations = useScheduleStore((s) => s.setReservations);
  const reservations = useScheduleStore((s) => s.reservations);
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

        const storedVersion = Number(localStorage.getItem(VERSION_KEY) || 0);
        const demoReservations = resvList.filter((r) =>
          DEMO_RESERVATION_IDS.includes(r.id)
        );

        if (reservations.length === 0 || storedVersion < MOCK_VERSION) {
          const existing =
            reservations.length > 0
              ? reservations.filter(
                  (r) => !DEMO_RESERVATION_IDS.includes(r.id)
                )
              : resvList.filter((r) => !DEMO_RESERVATION_IDS.includes(r.id));
          setReservations([...existing, ...demoReservations]);
          localStorage.setItem(VERSION_KEY, String(MOCK_VERSION));
        } else {
          const missing = demoReservations.filter(
            (d) => !reservations.find((r) => r.id === d.id)
          );
          if (missing.length > 0) {
            setReservations([...reservations, ...missing]);
          }
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

  return { loading, error, reservations };
}
