import { InstrumentSidebar } from './components/sidebar/InstrumentSidebar';
import { TopBar } from './components/layout/TopBar';
import { MainViewport } from './components/layout/MainViewport';
import { EditingDrawer } from './components/drawer/EditingDrawer';
import { useMockDataLoader } from './hooks/useMockDataLoader';

function App() {
  const { loading, error } = useMockDataLoader();

  if (loading) {
    return (
      <div className="h-full w-full flex items-center justify-center bg-base-50">
        <div className="text-center space-y-3">
          <div className="w-14 h-14 mx-auto rounded-2xl bg-gradient-to-br from-mint-400 to-sage-500 flex items-center justify-center text-white text-2xl shadow animate-pulse">
            🧫
          </div>
          <div>
            <p className="text-base-800 font-semibold">实验室仪器排期看板</p>
            <p className="text-xs text-base-500 mt-1">正在加载 mock 数据...</p>
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="h-full w-full flex items-center justify-center bg-base-50">
        <div className="text-center space-y-3 max-w-md px-6">
          <div className="text-5xl">⚠️</div>
          <div>
            <p className="text-red-700 font-semibold">加载失败</p>
            <p className="text-sm text-base-600 mt-1">{error}</p>
            <p className="text-xs text-base-500 mt-2">
              请确认 public/mock 下 JSON 文件存在，并通过 npm run dev 启动（以支持 fetch 静态资源）
            </p>
          </div>
          <button
            className="px-4 py-2 rounded-lg bg-mint-500 text-white text-sm hover:bg-mint-600 transition"
            onClick={() => window.location.reload()}
          >
            重新加载
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="h-full w-full flex flex-col bg-base-50">
      <TopBar />
      <div className="flex-1 flex min-h-0">
        <InstrumentSidebar />
        <MainViewport />
      </div>
      <EditingDrawer />
    </div>
  );
}

export default App;
