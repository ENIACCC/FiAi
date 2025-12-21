import { useState, useEffect } from 'react';
import { MainLayout } from '../layout/MainLayout';
import { StockList } from '../components/StockList';
import { Card, Tabs, Button, Modal, Input, App, Form, Space, Dropdown } from 'antd';
import { PlusOutlined, SettingOutlined } from '@ant-design/icons';
import * as api from '../api';
import { useStore } from '../store/useStore';

export const StockPage = () => {
  // Store
  const { setWatchlist, setActiveGroupId: setActiveGroupIdInStore } = useStore();
  const { message, modal } = App.useApp();

  // Group State
  const [groups, setGroups] = useState<any[]>([]);
  const [activeGroupId, setActiveGroupId] = useState<string>('default');

  // Watchlist State
  const [watchlistData, setWatchlistData] = useState<any[]>([]);
  const [loadingWatchlist, setLoadingWatchlist] = useState(false);

  // Modals
  const [isGroupModalVisible, setIsGroupModalVisible] = useState(false);
  const [isSearchModalVisible, setIsSearchModalVisible] = useState(false);
  const [isRenameModalVisible, setIsRenameModalVisible] = useState(false);
  const [renameTarget, setRenameTarget] = useState<any | null>(null);
  const [defaultGroupName, setDefaultGroupName] = useState<string>('默认分组');
  const [groupCounts, setGroupCounts] = useState<Record<string, number>>({});
  const [defaultCount, setDefaultCount] = useState<number>(0);
  
  // Search State
  const [searchResults, setSearchResults] = useState<any[]>([]);
  const [loadingSearch, setLoadingSearch] = useState(false);

  // Form for new group
  const [groupForm] = Form.useForm();
  const [renameForm] = Form.useForm();

  // Fetch Groups
  const fetchGroups = async () => {
    try {
      const res = await api.getWatchlistGroups();
      // Handle DRF ModelViewSet response (array or paginated results)
      const groupsData = Array.isArray(res.data) ? res.data : (res.data.results || []);
      setGroups(groupsData);
      
      // Initialize counts from groups if available
      const counts: Record<string, number> = {};
      groupsData.forEach((g: any) => {
        if (typeof g.item_count === 'number') counts[g.id] = g.item_count;
      });
      setGroupCounts(counts);
      
      // If activeGroupId is not in groups and not default, reset to default
      if (activeGroupId !== 'default' && !groupsData.find((g: any) => g.id === activeGroupId)) {
          setActiveGroupId('default');
      }
    } catch (error) {
      message.error('加载分组失败');
    }
  };

  // Fetch Watchlist
  const fetchWatchlist = async () => {
    setLoadingWatchlist(true);
    try {
      // If default, pass undefined as group_id
      const groupId = activeGroupId === 'default' ? undefined : activeGroupId;
      const res = await api.getWatchlist(groupId);
      if (res.data && res.data.status === 'success') {
        const listData = Array.isArray(res.data.data) ? res.data.data : [];
        setWatchlistData(listData);
        // Sync current group watchlist to store so StockList can show stars
        const codes = listData.map((item: any) => item.ts_code);
        setWatchlist(codes);
      }
    } catch (error) {
      message.error('加载自选失败');
    } finally {
      setLoadingWatchlist(false);
    }
  };

  useEffect(() => {
    (async () => {
      await fetchGroups();
      try {
        const res = await api.getWatchlistCount();
        if (res.data.status === 'success') {
          setDefaultCount(res.data.data.default || 0);
          setGroupCounts(res.data.data.groups || {});
        }
      } catch {}
    })();
  }, []);

  useEffect(() => {
    fetchWatchlist();
  }, [activeGroupId]);
  
  // Sync active group to global store so AIChat can access it
  useEffect(() => {
    setActiveGroupIdInStore(activeGroupId);
  }, [activeGroupId]);
  
  useEffect(() => {
    const saved = localStorage.getItem('default_group_name');
    if (saved) setDefaultGroupName(saved);
  }, []);

  // Handlers
  const handleCreateGroup = async (values: any) => {
    try {
      const res = await api.createWatchlistGroup(values.name);
      // DRF ModelViewSet returns 201 Created on success with the object
      if (res.status === 201) {
        message.success('创建分组成功');
        setIsGroupModalVisible(false);
        groupForm.resetFields();
        await fetchGroups(); // Wait for groups to reload
        
        // Switch to new group
        if (res.data.id) {
            setActiveGroupId(res.data.id);
        }
      } else {
        // Fallback for custom errors
        message.error(res.data.message || '创建失败');
      }
    } catch (error) {
      message.error('创建失败');
    }
  };

  const handleDeleteGroup = async (targetKey: string) => {
    try {
      await api.deleteWatchlistGroup(targetKey);
      message.success('删除分组成功');
      // If deleted active group, switch to default
      if (activeGroupId === targetKey) {
        setActiveGroupId('default');
      }
      fetchGroups();
    } catch (error) {
      message.error('删除失败');
    }
  };

  const handleEditGroup = (targetKey: any, action: 'add' | 'remove') => {
    if (action === 'add') {
      setIsGroupModalVisible(true);
    } else {
      modal.confirm({
        title: '确认删除',
        content: '删除分组将同时移除该分组下的所有自选股，确认继续吗？',
        onOk: () => handleDeleteGroup(targetKey),
      });
    }
  };

  const openRenameModal = (group: any) => {
    setRenameTarget(group);
    renameForm.setFieldsValue({ name: group.name });
    setIsRenameModalVisible(true);
  };

  const handleRenameGroup = async (values: any) => {
    if (!renameTarget) return;
    try {
      if (renameTarget.id === 'default') {
        setDefaultGroupName(values.name);
        localStorage.setItem('default_group_name', values.name);
        message.success('重命名成功');
        setIsRenameModalVisible(false);
        renameForm.resetFields();
      } else {
        const res = await api.updateWatchlistGroup(renameTarget.id, values.name);
        if (res.status === 200) {
          message.success('重命名成功');
          setIsRenameModalVisible(false);
          renameForm.resetFields();
          await fetchGroups();
        } else {
          message.error('重命名失败');
        }
      }
    } catch (error) {
      message.error('重命名失败');
    }
  };

  const handleSearch = async (val: string) => {
    if (!val) {
        setSearchResults([]);
        return;
    }
    setLoadingSearch(true);
    try {
      const res = await api.getStocks(val);
      if (res.data.status === 'success') {
        setSearchResults(res.data.data);
      }
    } catch (error) {
      message.error('搜索失败');
    } finally {
      setLoadingSearch(false);
    }
  };

  const handleAddToWatchlist = async (record: any) => {
    try {
      const groupId = activeGroupId === 'default' ? undefined : activeGroupId;
      const res = await api.addToWatchlist({
        ts_code: record.ts_code,
        name: record.name,
        group_id: groupId
      });
      if (res.data.status === 'success' || res.data.status === 'info') {
        if (res.data.status === 'success') {
          message.success('已添加到自选');
          setIsSearchModalVisible(false);
        } else {
          message.info('该股票已在当前分组');
        }
        fetchWatchlist();
        // Update counts locally
        if (activeGroupId === 'default') {
          setDefaultCount((c) => c + 1);
        } else {
          setGroupCounts((m) => ({ ...m, [activeGroupId]: (m[activeGroupId] || 0) + 1 }));
        }
      } else {
        message.error('添加失败');
      }
    } catch (error) {
      message.error('添加失败');
    }
  };

  const handleRemoveFromWatchlist = async (record: any) => {
    try {
      const groupId = activeGroupId === 'default' ? undefined : activeGroupId;
      await api.removeFromWatchlist(record.ts_code, groupId);
      message.success('移除成功');
      fetchWatchlist();
      // Update counts locally
      if (activeGroupId === 'default') {
        setDefaultCount((c) => Math.max(0, c - 1));
      } else {
        setGroupCounts((m) => ({ ...m, [activeGroupId]: Math.max(0, (m[activeGroupId] || 1) - 1) }));
      }
    } catch (error) {
      message.error('移除失败');
    }
  };

  // Tabs Items
  const items = [
    { 
      label: (<span>{defaultGroupName} ({defaultCount})</span>), 
      key: 'default', 
      closable: false 
    },
    ...groups.map(g => ({
      label: (<span>{g.name} ({groupCounts[g.id] || 0})</span>),
      key: g.id,
      closable: true
    }))
  ];

  const manageMenuItems = [
    { key: 'rename', label: '重命名当前分组' },
    { key: 'delete', label: '删除当前分组' },
    { key: 'create', label: '新建分组' },
  ];

  const handleManageClick = (key: string) => {
    if (key === 'rename') {
      if (activeGroupId === 'default') {
        openRenameModal({ id: 'default', name: defaultGroupName });
      } else {
        const g = groups.find(x => x.id === activeGroupId);
        if (g) openRenameModal(g);
      }
    } else if (key === 'delete') {
      if (activeGroupId === 'default') {
        message.info('默认分组不可删除');
        return;
      }
      // Confirm delete
      modal.confirm({
        title: '确认删除',
        content: '删除分组将同时移除该分组下的所有自选股，确认继续吗？',
        onOk: () => handleDeleteGroup(activeGroupId),
      });
    } else if (key === 'create') {
      setIsGroupModalVisible(true);
    }
  };

  return (
    <MainLayout>
      <Card 
        variant="borderless" 
        title={
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <span>我的自选股</span>
                <Space>
                  <Dropdown 
                    menu={{ items: manageMenuItems, onClick: ({ key }) => handleManageClick(String(key)) }}
                    placement="bottomRight"
                    trigger={['hover']}
                  >
                    <Button 
                      type="text" 
                      shape="circle" 
                      className="gear-btn"
                      icon={<SettingOutlined />} 
                      style={{ 
                        border: '1px solid #d9d9d9', 
                        borderRadius: 20, 
                        width: 32, 
                        height: 32, 
                        padding: 0,
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center'
                      }}
                    />
                  </Dropdown>
                  <Button 
                      type="primary" 
                      icon={<PlusOutlined />} 
                      onClick={() => {
                          setSearchResults([]);
                          setIsSearchModalVisible(true);
                      }}
                  >
                      添加股票
                  </Button>
                </Space>
            </div>
        }
      >
        <Tabs
          type="editable-card"
          onChange={setActiveGroupId}
          activeKey={activeGroupId}
          onEdit={handleEditGroup}
          items={items}
          addIcon={<Space><PlusOutlined /> 新建分组</Space>}
        />
        
        <StockList 
            data={watchlistData} 
            loading={loadingWatchlist} 
            actionType="remove"
            onAction={handleRemoveFromWatchlist}
            height="calc(100vh - 300px)"
        />
      </Card>

      {/* Create Group Modal */}
      <Modal
        title="新建自选分组"
        open={isGroupModalVisible}
        onCancel={() => setIsGroupModalVisible(false)}
        footer={null}
      >
        <Form form={groupForm} onFinish={handleCreateGroup}>
            <Form.Item 
                name="name" 
                rules={[{ required: true, message: '请输入分组名称' }]}
            >
                <Input placeholder="例如：医药股、ETF、高股息..." />
            </Form.Item>
            <Form.Item style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: 0 }}>
                <Button onClick={() => setIsGroupModalVisible(false)} style={{ marginRight: 8 }}>取消</Button>
                <Button type="primary" htmlType="submit">创建</Button>
            </Form.Item>
        </Form>
      </Modal>
      
      <Modal
        title="重命名分组"
        open={isRenameModalVisible}
        onCancel={() => setIsRenameModalVisible(false)}
        footer={null}
      >
        <Form form={renameForm} onFinish={handleRenameGroup}>
          <Form.Item 
            name="name" 
            rules={[{ required: true, message: '请输入新的分组名称' }]}
          >
            <Input placeholder="新的分组名称" />
          </Form.Item>
          <Form.Item style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: 0 }}>
            <Button onClick={() => setIsRenameModalVisible(false)} style={{ marginRight: 8 }}>取消</Button>
            <Button type="primary" htmlType="submit">保存</Button>
          </Form.Item>
        </Form>
      </Modal>

      {/* Search Stock Modal */}
      <Modal
        title={`添加股票到 "${activeGroupId === 'default' ? defaultGroupName : groups.find(g => g.id === activeGroupId)?.name || ''}"`}
        open={isSearchModalVisible}
        onCancel={() => setIsSearchModalVisible(false)}
        footer={null}
        width={800}
      >
        <Input.Search 
            placeholder="输入代码或名称搜索" 
            enterButton 
            onSearch={handleSearch}
            loading={loadingSearch}
            style={{ marginBottom: 16 }}
            allowClear
        />
        <StockList 
            data={searchResults} 
            loading={loadingSearch} 
            actionType="add"
            onAction={handleAddToWatchlist}
            height={400}
        />
      </Modal>
    </MainLayout>
  );
};
