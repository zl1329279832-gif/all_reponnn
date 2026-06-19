import { App } from './App';

async function main() {
  const container = document.getElementById('app')!;
  const app = new App(container);
  await app.init();
  app.start();
  (window as any).__app = app;
}

main().catch(err => {
  console.error('App init failed', err);
  const el = document.getElementById('app');
  if (el) el.innerHTML = `<div style="padding:24px;color:#ef4444;font-family:sans-serif">初始化失败: ${String(err)}</div>`;
});
