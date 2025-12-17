import { Layout, Menu, Button, Drawer, theme, Grid } from 'antd';
import { 
  MenuOutlined, DashboardOutlined, StockOutlined, 
  ThunderboltOutlined, SettingOutlined, MessageOutlined,
  SunOutlined, MoonOutlined, StarOutlined
} from '@ant-design/icons';
import { useState } from 'react';
import { useStore } from '../store/useStore';
import { AIChat } from '../components/AIChat';
import { useNavigate, useLocation } from 'react-router-dom';

const { Header, Sider, Content } = Layout;
const { useBreakpoint } = Grid;

export const MainLayout = ({ children }: { children: React.ReactNode }) => {
  const screens = useBreakpoint();
  const isMobile = !screens.md; // < 768px
  const [menuOpen, setMenuOpen] = useState(false);
  const [collapsed, setCollapsed] = useState(true);
  const [aiOpen, setAiOpen] = useState(false);
  const [pcAiCollapsed, setPcAiCollapsed] = useState(true); // Default to collapsed (closed)
  const { isDark, toggleTheme } = useStore();
  const { token } = theme.useToken();
  const navigate = useNavigate();
  const location = useLocation();

  const MenuItems = [
    { key: '/', icon: <DashboardOutlined />, label: '市场概览' },
    { key: '/stocks', icon: <StockOutlined />, label: '股票数据' },
    { key: '/analysis', icon: <ThunderboltOutlined />, label: '技术分析' },
    { key: '/settings', icon: <SettingOutlined />, label: '设置' },
  ];

  const handleMenuClick = ({ key }: { key: string }) => {
    navigate(key);
    setMenuOpen(false);
  };

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Header style={{ 
        padding: '0 16px', 
        background: token.colorBgContainer, 
        display: 'flex', 
        alignItems: 'center', 
        justifyContent: 'space-between',
        borderBottom: `1px solid ${token.colorBorderSecondary}`,
        position: 'sticky',
        top: 0,
        zIndex: 1000,
        width: '100%'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
          {isMobile && (
            <Button icon={<MenuOutlined />} onClick={() => setMenuOpen(true)} />
          )}
          <div style={{ fontSize: 20, fontWeight: 'bold', color: token.colorPrimary }}>Trae 金融</div>
        </div>
        
        <div style={{ display: 'flex', gap: 12 }}>
          <Button shape="circle" icon={isDark ? <SunOutlined /> : <MoonOutlined />} onClick={toggleTheme} />
          {isMobile && (
            <Button shape="circle" icon={<MessageOutlined />} onClick={() => setAiOpen(true)} type="primary" ghost />
          )}
        </div>
      </Header>
      
      <Layout>
        {/* PC Left Sider */}
        {!isMobile && (
          <Sider 
            width={200} 
            collapsible
            collapsed={collapsed}
            onCollapse={(value) => setCollapsed(value)}
            theme={isDark ? 'dark' : 'light'} 
            style={{ borderRight: `1px solid ${token.colorBorderSecondary}` }}
          >
            <Menu 
              mode="inline" 
              selectedKeys={[location.pathname]} 
              items={MenuItems} 
              onClick={handleMenuClick}
              style={{ height: '100%', borderRight: 0 }} 
            />
          </Sider>
        )}

        <Content style={{ padding: 16, overflow: 'auto' }}>
          {children}
        </Content>

        {/* PC Right Sider (AI) */}
        {!isMobile && (
          <Sider 
            width={320} 
            collapsible 
            collapsed={pcAiCollapsed} 
            onCollapse={setPcAiCollapsed}
            collapsedWidth={0}
            theme={isDark ? 'dark' : 'light'}
            style={{ borderLeft: `1px solid ${token.colorBorderSecondary}` }}
            trigger={null}
          >
             <div style={{ height: '100%', display: pcAiCollapsed ? 'none' : 'block' }}>
               <AIChat open={true} onClose={() => {}} isMobile={false} />
             </div>
          </Sider>
        )}
        {!isMobile && (
           <Button 
             icon={<MessageOutlined />} 
             style={{ position: 'fixed', right: pcAiCollapsed ? 16 : 336, bottom: 16, zIndex: 100, transition: 'right 0.2s' }}
             onClick={() => setPcAiCollapsed(!pcAiCollapsed)}
             shape="circle"
             type="primary"
             size="large"
           />
        )}
      </Layout>

      {/* Mobile Drawers */}
      <Drawer title="菜单" placement="left" onClose={() => setMenuOpen(false)} open={menuOpen} width={240}>
        <Menu 
          mode="inline" 
          selectedKeys={[location.pathname]} 
          items={MenuItems} 
          onClick={handleMenuClick} 
        />
      </Drawer>

      <Drawer title="AI 助手" placement="right" onClose={() => setAiOpen(false)} open={aiOpen} width="100%">
        <AIChat open={aiOpen} onClose={() => setAiOpen(false)} isMobile={true} />
      </Drawer>
    </Layout>
  );
};
