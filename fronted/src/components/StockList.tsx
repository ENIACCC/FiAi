import { Table, Button, Input, Space, Tag, Popconfirm } from 'antd';
import { StarFilled, DeleteOutlined, PlusOutlined } from '@ant-design/icons';
import { useStore } from '../store/useStore';

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
  const { watchlist } = useStore();

  const columns = [
    { title: '代码', dataIndex: 'ts_code', width: 100, render: (text: string) => <Tag>{text}</Tag> },
    { title: '名称', dataIndex: 'name', width: 120, render: (text: string, record: any) => (
      <Space>
        <span style={{ fontWeight: 500 }}>{text}</span>
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
    { title: '市盈率', dataIndex: 'pe', width: 100, render: (val: number) => val ? val.toFixed(2) : '-' },
    { title: '行业', dataIndex: 'industry', width: 100, render: (text: string) => text || '-' },
    { title: '总市值', dataIndex: 'market_cap', width: 120, render: (val: number) => val ? (val / 100000000).toFixed(2) + '亿' : '-' },
    {
      title: '操作',
      key: 'action',
      width: 100,
      fixed: 'right' as const,
      render: (_: any, record: any) => {
        if (actionType === 'remove') {
            return (
                <Popconfirm title="确定移出该分组吗？" onConfirm={() => onAction && onAction(record)}>
                    <Button danger type="text" icon={<DeleteOutlined />}>移除</Button>
                </Popconfirm>
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
