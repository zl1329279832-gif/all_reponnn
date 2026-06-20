import { useToastStore, type ToastKind } from '../../store/toastStore';

const colorMap: Record<ToastKind, string> = {
  success: 'border-mint-300 bg-mint-50 text-mint-800',
  error: 'border-red-300 bg-red-50 text-red-800',
  warning: 'border-amber-300 bg-amber-50 text-amber-800',
  info: 'border-base-200 bg-white text-base-800',
};

const iconMap: Record<ToastKind, string> = {
  success: '✓',
  error: '✕',
  warning: '⚠',
  info: 'ℹ',
};

export function ToastContainer() {
  const items = useToastStore((s) => s.items);
  const remove = useToastStore((s) => s.remove);

  return (
    <div className="fixed top-4 right-4 z-[100] flex flex-col gap-2 max-w-sm w-full pointer-events-none">
      {items.map((t) => (
        <div
          key={t.id}
          onClick={() => remove(t.id)}
          className={`pointer-events-auto shadow-md rounded-lg border px-4 py-3 text-sm flex items-start gap-2 cursor-pointer animate-[slideIn_0.25s_ease-out] ${colorMap[t.kind]}`}
        >
          <span className="mt-0.5 font-bold">{iconMap[t.kind]}</span>
          <p className="flex-1 leading-snug">{t.message}</p>
        </div>
      ))}
      <style>{`
        @keyframes slideIn {
          from { transform: translateX(20px); opacity: 0; }
          to { transform: translateX(0); opacity: 1; }
        }
      `}</style>
    </div>
  );
}
