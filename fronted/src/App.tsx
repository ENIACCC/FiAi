import { ConfigProvider, theme } from 'antd';
import zhCN from 'antd/locale/zh_CN';
import { useStore } from './store/useStore';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { Login } from './pages/Login';
import { Register } from './pages/Register';
import { Dashboard } from './pages/Dashboard';
import { StockPage } from './pages/StockPage';
import { WatchlistPage } from './pages/WatchlistPage';

const AuthGuard = ({ children }: { children: JSX.Element }) => {
  // const token = useStore((state) => state.token);
  // if (!token) {
  //   return <Navigate to="/login" replace />;
  // }
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
          {/* Placeholders for other routes */}
          <Route path="/analysis" element={
            <AuthGuard>
              <Dashboard /> {/* Placeholder */}
            </AuthGuard>
          } />
           <Route path="/settings" element={
            <AuthGuard>
              <Dashboard /> {/* Placeholder */}
            </AuthGuard>
          } />
        </Routes>
      </BrowserRouter>
    </ConfigProvider>
  )
}

export default App
