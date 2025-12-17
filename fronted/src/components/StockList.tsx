import { Table, Button, Input, Space, message, Segmented, Tag } from 'antd';
import { StarFilled, AppstoreOutlined, StarOutlined } from '@ant-design/icons';
import { useState, useMemo } from 'react';
import { useStore } from '../store/useStore';
import * as api from '../api';

export const StockList = ({ data, loading, onSearch }: { data: any[]; loading: boolean; onSearch: (val: string) => void }) => {
  const { watchlist, addToWatchlist, removeFromWatchlist } = useStore();
  const [filterMode, setFilterMode] = useState<'all' | 'watchlist'>('all');

  const handleToggleWatchlist = async (record: any) => {
    try {
      if (watchlist.has(record.ts_code)) {
        await api.removeFromWatchlist(record.ts_code);
        removeFromWatchlist(record.ts_code);
        message.success(`已从自选移除: ${record.name}`);
      } else {
        await api.addToWatchlist({ ts_code: record.ts_code, name: record.name });
        addToWatchlist(record.ts_code);
        message.success(`已加入自选: ${record.name}`);
      }
    } catch (error) {
      message.error('操作失败');
      console.error(error);
    }
  };

  // We rely on backend search now for 'all' mode with searchText
  // But for 'watchlist' mode, we might still want to filter locally? 
  // Or just display watchlist.
  
  const filteredData = useMemo(() => {
    // If we have data from backend (which is already filtered by search if onSearch called),
    // we just need to filter by watchlist if mode is watchlist.
    if (filterMode === 'watchlist') {
        return data.filter(item => watchlist.has(item.ts_code));
    }
    return data;
  }, [data, filterMode, watchlist]);

  const columns = [
    { title: '代码', dataIndex: 'ts_code', width: 100, render: (text: string) => <Tag>{text}</Tag> },
    { title: '名称', dataIndex: 'name', width: 120, render: (text: string, record: any) => (
      <Space>
        <span style={{ fontWeight: 500 }}>{text}</span>
        {watchlist.has(record.ts_code) && <StarFilled style={{ color: '#faad14' }} />}
      </Space>
    )},
    { title: '最新价', dataIndex: 'price', width: 100, render: (val: number, record: any) => (
        <span style={{ color: record.change_pct > 0 ? '#ff4d4f' : record.change_pct < 0 ? '#52c41a' : 'inherit' }}>
            {val}
        </span>
    )},
    { title: '涨跌幅%', dataIndex: 'change_pct', width: 100, render: (val: number) => (
        <span style={{ color: val > 0 ? '#ff4d4f' : val < 0 ? '#52c41a' : 'inherit' }}>
            {val > 0 ? '+' : ''}{val}%
        </span>
    )},
    { title: '换手率%', dataIndex: 'turnover_rate', width: 100, render: (val: number) => val ? `${val}%` : '-' },
    { title: '市盈率', dataIndex: 'pe', width: 100, render: (val: number) => val ? val.toFixed(2) : '-' },
    {
      title: '操作',
      key: 'action',
      width: 100,
      render: (_: any, record: any) => (
        <Button 
          type={watchlist.has(record.ts_code) ? 'default' : 'primary'}
          ghost={!watchlist.has(record.ts_code)}
          size="small"
          icon={watchlist.has(record.ts_code) ? <StarFilled /> : <StarOutlined />}
          onClick={() => handleToggleWatchlist(record)}
        >
          {watchlist.has(record.ts_code) ? '已关注' : '关注'}
        </Button>
      ),
    },
  ];

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <Segmented
          options={[
            { label: '全部股票', value: 'all', icon: <AppstoreOutlined /> },
            { label: '我的自选', value: 'watchlist', icon: <StarFilled /> },
          ]}
          value={filterMode}
          onChange={(value) => setFilterMode(value as 'all' | 'watchlist')}
        />

        <Input.Search 
          placeholder="搜索股票代码/名称" 
          allowClear
          style={{ width: 260 }} 
          onSearch={val => onSearch(val)}
          // Trigger search on enter or clear
        />
      </div>

      <Table 
        columns={columns} 
        dataSource={filteredData} 
        rowKey="ts_code" 
        loading={loading}
        scroll={{ x: 600 }}
        pagination={{ 
          pageSize: 10,
          showTotal: (total) => `共 ${total} 条数据`
        }}
      />
    </div>
  );
};
