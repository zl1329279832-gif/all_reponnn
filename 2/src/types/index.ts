export type InstrumentCategory = '光谱类' | '色谱类' | '显微类' | '分析类';

export interface Instrument {
  id: string;
  name: string;
  category: InstrumentCategory;
  model: string;
  location: string;
  description?: string;
}

export interface Reservation {
  id: string;
  instrumentId: string;
  experimentName: string;
  owner: string;
  sampleCount: number;
  remarks?: string;
  startTime: string;
  endTime: string;
  createdAt: string;
}

export type ViewMode = 'board' | 'calendar';

export interface ScheduleState {
  instruments: Instrument[];
  reservations: Reservation[];
  selectedInstrumentIds: string[];
  currentWeekStart: string;
  viewMode: ViewMode;
  editingReservationId: string | null;
  drawerOpen: boolean;
}
