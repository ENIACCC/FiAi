import { MainLayout } from '../layout/MainLayout';
import { useEffect, useState } from 'react';
import { Card, Table, Typography, Tag, Space, Button } from 'antd';
import { ThunderboltOutlined, ReloadOutlined } from '@ant-design/icons';
import axios from 'axios';

const { Paragraph } = Typography;

interface AnalysisLog {
  id: number;
  ts_code: string;
  stock_name: string;
  analysis_content: string;
  created_at: string;
}

export const AnalysisHistory = () => {
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState<AnalysisLog[]>([]);

  const fetchData = async () => {
    setLoading(true);
    try {
      const res = await axios.get('http://127.0.0.1:8000/api/ai-history/');
      // Handle both paginated and non-paginated responses just in case
      const results = Array.isArray(res.data) ? res.data : (res.data.results || []);
      setData(results);
    } catch (error) {
      console.error("Failed to fetch history", error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const columns = [
    {
      title: '分析时间',
      dataIndex: 'created_at',
      key: 'created_at',
      render: (text: string) => new Date(text).toLocaleString(),
      width: 200,
    },
    {
      title: '对象',
      key: 'stock',
      render: (_: any, record: AnalysisLog) => (
        <Space>
            <Tag color={record.ts_code === 'PORTFOLIO' ? 'purple' : 'blue'}>
                {record.stock_name || record.ts_code}
            </Tag>
            {record.ts_code !== 'PORTFOLIO' && <span style={{fontSize: 12, color: '#999'}}>{record.ts_code}</span>}
        </Space>
      ),
      width: 200,
    },
    {
      title: '分析内容',
      dataIndex: 'analysis_content',
      key: 'analysis_content',
      render: (text: string) => (
        <Paragraph 
            ellipsis={{ rows: 3, expandable: true, symbol: '展开' }}
            style={{ whiteSpace: 'pre-line', margin: 0 }}
        >
          {text}
        </Paragraph>
      ),
    },
  ];

  return (
    <MainLayout>
      <Card 
        variant="borderless"
        title={
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <ThunderboltOutlined />
            <span>AI 分析历史</span>
          </div>
        }
        extra={
          <Button icon={<ReloadOutlined />} onClick={fetchData} loading={loading}>
            刷新
          </Button>
        }
        className="shadow-sm"
      >
        <Table 
          columns={columns} 
          dataSource={data} 
          rowKey="id" 
          loading={loading}
          pagination={{ pageSize: 10 }}
        />
      </Card>
    </MainLayout>
  );
};
