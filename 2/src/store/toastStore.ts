import { create } from 'zustand';

export type ToastKind = 'success' | 'error' | 'warning' | 'info';

export interface ToastItem {
  id: string;
  kind: ToastKind;
  message: string;
  duration: number;
}

interface ToastStore {
  items: ToastItem[];
  push: (message: string, kind?: ToastKind, duration?: number) => void;
  remove: (id: string) => void;
}

let counter = 0;

export const useToastStore = create<ToastStore>((set, get) => ({
  items: [],
  push: (message, kind = 'info', duration = 2600) => {
    const id = `t-${Date.now()}-${++counter}`;
    set({ items: [...get().items, { id, kind, message, duration }] });
    if (duration > 0) {
      setTimeout(() => {
        get().remove(id);
      }, duration);
    }
  },
  remove: (id) => {
    set({ items: get().items.filter((x) => x.id !== id) });
  },
}));

export function toast(message: string, kind: ToastKind = 'info', duration = 2600) {
  useToastStore.getState().push(message, kind, duration);
}
