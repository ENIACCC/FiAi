import { Layout, Menu, Button, Drawer, theme, Grid, Dropdown, Avatar } from 'antd';
import { 
  MenuOutlined, DashboardOutlined, 
  ThunderboltOutlined, SettingOutlined, MessageOutlined,
  SunOutlined, MoonOutlined, LogoutOutlined, UserOutlined, StarOutlined, ExperimentOutlined
} from '@ant-design/icons';
import { useEffect, useMemo, useState } from 'react';
import { useStore } from '../store/useStore';
import { AIChat } from '../components/AIChat';
import { useNavigate, useLocation } from 'react-router-dom';
import type { MenuProps } from 'antd';

const { Header, Sider, Content } = Layout;
const { useBreakpoint } = Grid;

export const MainLayout = ({ children }: { children: React.ReactNode }) => {
  const screens = useBreakpoint();
  const isMobile = !screens.md; // < 768px
  const [menuOpen, setMenuOpen] = useState(false);
  const [collapsed, setCollapsed] = useState(true);
  const { isDark, toggleTheme, logout, username, isAiChatOpen, setAiChatOpen } = useStore();
  const { token } = theme.useToken();
  const navigate = useNavigate();
  const location = useLocation();
  const [aiWidth, setAiWidth] = useState<number>(() => {
    const raw = window.localStorage.getItem('aiChatWidth');
    const v = raw ? Number(raw) : 360;
    return Number.isFinite(v) ? Math.min(Math.max(v, 280), 720) : 360;
  });
  const [isResizingAI, setIsResizingAI] = useState(false);

  const buttonRight = useMemo(() => {
    return !isMobile && isAiChatOpen ? aiWidth + 16 : 16;
  }, [aiWidth, isAiChatOpen, isMobile]);

  useEffect(() => {
    window.localStorage.setItem('aiChatWidth', String(aiWidth));
  }, [aiWidth]);

  useEffect(() => {
    if (!isResizingAI) return;
    const onMove = (e: MouseEvent) => {
      const target = window.innerWidth - e.clientX;
      const next = Math.min(Math.max(target, 280), 720);
      setAiWidth(next);
    };
    const onUp = () => {
      setIsResizingAI(false);
    };
    window.addEventListener('mousemove', onMove);
    window.addEventListener('mouseup', onUp);
    return () => {
      window.removeEventListener('mousemove', onMove);
      window.removeEventListener('mouseup', onUp);
    };
  }, [isResizingAI]);

  const MenuItems = [
    { key: '/', icon: <DashboardOutlined />, label: '市场概览' },
    { key: '/watchlist', icon: <StarOutlined />, label: '自选&分组' },
    { key: '/strategy', icon: <ExperimentOutlined />, label: '策略实验室' },
    { key: '/analysis', icon: <ThunderboltOutlined />, label: '技术分析' },
    { key: '/settings', icon: <SettingOutlined />, label: '设置' },
  ];

  const handleMenuClick = ({ key }: { key: string }) => {
    navigate(key);
    setMenuOpen(false);
  };
  
  const handleLogout = () => {
      logout();
      navigate('/login');
  };

  const userMenu: MenuProps['items'] = [
    {
      key: 'settings',
      label: '设置',
      icon: <SettingOutlined />,
      onClick: () => navigate('/settings'),
    },
    {
      type: 'divider',
    },
    {
      key: 'logout',
      label: '退出登录',
      icon: <LogoutOutlined />,
      onClick: handleLogout,
    },
  ];

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
        
        <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
          <Button shape="circle" icon={isDark ? <SunOutlined /> : <MoonOutlined />} onClick={toggleTheme} />
          
          <Dropdown menu={{ items: userMenu }} placement="bottomRight">
            <div style={{ cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 8 }}>
              <Avatar icon={<UserOutlined />} style={{ backgroundColor: token.colorPrimary }} />
              {!isMobile && <span>{username || 'User'}</span>}
            </div>
          </Dropdown>

          {isMobile && (
            <Button shape="circle" icon={<MessageOutlined />} onClick={() => setAiChatOpen(true)} type="primary" ghost />
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
            style={{ 
              borderRight: `1px solid ${token.colorBorderSecondary}`,
              overflow: 'auto',
              height: 'calc(100vh - 64px)',
              position: 'sticky',
              top: 64,
            }}
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
            width={aiWidth} 
            collapsible 
            collapsed={!isAiChatOpen} 
            onCollapse={(val) => setAiChatOpen(!val)}
            collapsedWidth={0}
            theme={isDark ? 'dark' : 'light'}
            style={{ 
              borderLeft: `1px solid ${token.colorBorderSecondary}`,
              height: 'calc(100vh - 64px)',
              position: 'sticky',
              top: 64,
              overflow: 'hidden',
            }}
            trigger={null}
          >
             <div
               onMouseDown={(e) => {
                 if (!isAiChatOpen) return;
                 e.preventDefault();
                 setIsResizingAI(true);
               }}
               style={{
                 position: 'absolute',
                 left: 0,
                 top: 0,
                 bottom: 0,
                 width: 6,
                 cursor: 'col-resize',
                 zIndex: 10,
               }}
             />
             <div style={{ height: '100%', display: !isAiChatOpen ? 'none' : 'block' }}>
               <AIChat open={true} onClose={() => {}} isMobile={false} />
             </div>
          </Sider>
        )}
        {!isMobile && (
           <Button 
             icon={<MessageOutlined />} 
             style={{ position: 'fixed', right: buttonRight, bottom: 16, zIndex: 100, transition: 'right 0.2s' }}
             onClick={() => setAiChatOpen(!isAiChatOpen)}
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

      {isMobile && (
        <Drawer title="AI 助手" placement="right" onClose={() => setAiChatOpen(false)} open={isAiChatOpen} width="100%">
          <AIChat open={isAiChatOpen} onClose={() => setAiChatOpen(false)} isMobile={true} />
        </Drawer>
      )}
    </Layout>
  );
};
