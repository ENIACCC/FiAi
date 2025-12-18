import { useState, useEffect } from 'react';
import { MainLayout } from '../layout/MainLayout';
import { StockList } from '../components/StockList';
import { Card, Tabs, Button, Modal, Input, App, Form, Space } from 'antd';
import { PlusOutlined } from '@ant-design/icons';
import * as api from '../api';
import { useStore } from '../store/useStore';

export const StockPage = () => {
  // Store
  const { setWatchlist } = useStore();
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
  
  // Search State
  const [searchResults, setSearchResults] = useState<any[]>([]);
  const [loadingSearch, setLoadingSearch] = useState(false);

  // Form for new group
  const [groupForm] = Form.useForm();

  // Fetch Groups
  const fetchGroups = async () => {
    try {
      const res = await api.getWatchlistGroups();
      // Handle DRF ModelViewSet response (array or paginated results)
      const groupsData = Array.isArray(res.data) ? res.data : (res.data.results || []);
      setGroups(groupsData);
      
      // If activeGroupId is not in groups and not default, reset to default
      if (activeGroupId !== 'default' && !groupsData.find((g: any) => g.id === activeGroupId)) {
          setActiveGroupId('default');
      }
    } catch (error) {
      console.error(error);
    }
  };

  // Fetch Watchlist
  const fetchWatchlist = async () => {
    setLoadingWatchlist(true);
    try {
      // If default, pass undefined as group_id
      const groupId = activeGroupId === 'default' ? undefined : activeGroupId;
      const res = await api.getWatchlist(groupId);
      if (res.data.status === 'success') {
        setWatchlistData(res.data.data);
        // Sync current group watchlist to store so StockList can show stars
        const codes = res.data.data.map((item: any) => item.ts_code);
        setWatchlist(codes);
      }
    } catch (error) {
      console.error(error);
    } finally {
      setLoadingWatchlist(false);
    }
  };

  useEffect(() => {
    fetchGroups();
  }, []);

  useEffect(() => {
    fetchWatchlist();
  }, [activeGroupId]);

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
      console.error(error);
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
        message.success(res.data.message);
        fetchWatchlist();
      } else {
        message.error(res.data.message);
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
    } catch (error) {
      message.error('移除失败');
    }
  };

  // Tabs Items
  const items = [
    { label: '默认分组', key: 'default', closable: false },
    ...groups.map(g => ({ label: g.name, key: g.id, closable: true }))
  ];

  return (
    <MainLayout>
      <Card 
        variant="borderless" 
        title={
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <span>我的自选股</span>
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

      {/* Search Stock Modal */}
      <Modal
        title={`添加股票到 "${activeGroupId === 'default' ? '默认分组' : groups.find(g => g.id === activeGroupId)?.name || ''}"`}
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