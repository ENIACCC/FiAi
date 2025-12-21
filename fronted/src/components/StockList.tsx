import { Table, Button, Input, Space, Tag, Popconfirm } from 'antd';
import { StarFilled, DeleteOutlined, PlusOutlined, MessageOutlined } from '@ant-design/icons';
import { useStore } from '../store/useStore';
import { useNavigate } from 'react-router-dom';

interface StockListProps {
  data: any[];
  loading: boolean;
  onSearch?: (val: string) => void;
  actionType?: 'add' | 'remove';
  onAction?: (record: any) => void;
  height?: number | string;
}

export const StockList = ({ 
  data, 
  loading, 
  onSearch, 
  actionType = 'add', 
  onAction,
  height 
}: StockListProps) => {
  const { watchlist, setAiChatOpen, setAiContext } = useStore();
  const navigate = useNavigate();

  const handleAiChat = (record: any) => {
    setAiContext({
      type: 'stock',
      data: record
    });
    setAiChatOpen(true);
  };

  const columns = [
    {
      title: '代码',
      dataIndex: 'ts_code',
      width: 120,
      render: (text: string) => (
        <Tag style={{ cursor: 'pointer' }} onClick={() => navigate(`/stocks/${text}`)}>
          {text}
        </Tag>
      ),
    },
    { title: '名称', dataIndex: 'name', width: 160, render: (text: string, record: any) => (
      <Space>
        <Button type="link" style={{ padding: 0, height: 22 }} onClick={() => navigate(`/stocks/${record.ts_code}`)}>
          {text}
        </Button>
        {watchlist.has(record.ts_code) && <StarFilled style={{ color: '#faad14', fontSize: 12 }} />}
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
    { title: '总市值', dataIndex: 'market_cap', width: 120, render: (val: number) => val ? (val / 100000000).toFixed(2) + '亿' : '-' },
    {
      title: '操作',
      key: 'action',
      width: 180,
      fixed: 'right' as const,
      render: (_: any, record: any) => {
        if (actionType === 'remove') {
            return (
                <Space>
                    <Button 
                      type="text" 
                      icon={<MessageOutlined />}
                      style={{ color: '#1677ff' }}
                      onClick={() => handleAiChat(record)}
                    >
                      AI聊股
                    </Button>
                    <Popconfirm title="确定移出该分组吗？" onConfirm={() => onAction && onAction(record)}>
                        <Button danger type="text" icon={<DeleteOutlined />}>移除</Button>
                    </Popconfirm>
                </Space>
            )
        }
        return (
            <Button 
              type="primary"
              ghost
              size="small"
              icon={<PlusOutlined />}
              onClick={() => onAction && onAction(record)}
            >
              添加
            </Button>
        );
      },
    },
  ];

  return (
    <div>
      {onSearch && (
        <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'flex-end' }}>
            <Input.Search 
            placeholder="搜索股票代码/名称" 
            allowClear
            style={{ width: 260 }} 
            onSearch={val => onSearch(val)}
            />
        </div>
      )}

      <Table 
        columns={columns} 
        dataSource={data} 
        rowKey="ts_code" 
        loading={loading}
        scroll={{ x: 800, y: height }}
        pagination={{ 
          pageSize: 10,
          showTotal: (total) => `共 ${total} 条数据`
        }}
      />
    </div>
  );
};
