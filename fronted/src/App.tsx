import { ConfigProvider, theme, App as AntdApp } from 'antd';
import zhCN from 'antd/locale/zh_CN';
import { useStore } from './store/useStore';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { Login } from './pages/Login';
import { Register } from './pages/Register';
import { Dashboard } from './pages/Dashboard';
import { StockPage } from './pages/StockPage';
import { StockResearch } from './pages/StockResearch';
import { AnalysisHistory } from './pages/AnalysisHistory';
import { Settings } from './pages/Settings';
import { StrategyLab } from './pages/StrategyLab';
import { BacktestReport } from './pages/BacktestReport';

const AuthGuard = ({ children }: { children: JSX.Element }) => {
  const token = useStore((state) => state.token);
  if (!token) {
    return <Navigate to="/login" replace />;
  }
  return children;
};

function App() {
  const isDark = useStore((state) => state.isDark);

  return (
    <ConfigProvider
      locale={zhCN}
      theme={{
        algorithm: isDark ? theme.darkAlgorithm : theme.defaultAlgorithm,
        token: {
          colorPrimary: '#1677ff',
        },
      }}
    >
      <AntdApp>
        <BrowserRouter>
          <Routes>
            <Route path="/login" element={<Login />} />
            <Route path="/register" element={<Register />} />
            <Route path="/" element={
              <AuthGuard>
                <Dashboard />
              </AuthGuard>
            } />
            <Route path="/stocks" element={
              <AuthGuard>
                <StockPage />
              </AuthGuard>
            } />
            <Route path="/stocks/:ts_code" element={
              <AuthGuard>
                <StockResearch />
              </AuthGuard>
            } />
            <Route path="/watchlist" element={
              <AuthGuard>
                <StockPage />
              </AuthGuard>
            } />
            {/* Placeholders for other routes */}
            <Route path="/analysis" element={
              <AuthGuard>
                <AnalysisHistory />
              </AuthGuard>
            } />
            <Route path="/strategy" element={
              <AuthGuard>
                <StrategyLab />
              </AuthGuard>
            } />
            <Route path="/backtest-report" element={
              <AuthGuard>
                <BacktestReport />
              </AuthGuard>
            } />
             <Route path="/settings" element={
              <AuthGuard>
                <Settings />
              </AuthGuard>
            } />
          </Routes>
        </BrowserRouter>
      </AntdApp>
    </ConfigProvider>
  )
}

export default App
