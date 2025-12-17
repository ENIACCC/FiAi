import { useEffect, useState } from 'react';
import { MainLayout } from '../layout/MainLayout';
import { StockChart } from '../components/StockChart';
import { useStore } from '../store/useStore';
import { Card, Row, Col, Statistic, Spin } from 'antd';
import { ArrowUpOutlined, ArrowDownOutlined } from '@ant-design/icons';
import { useStockData } from '../hooks/useStockData';
import * as api from '../api';

export const Dashboard = () => {
  const { isDark } = useStore();
  // const { data } = useStockData(); // Replaced by top gainers fetch
  const [indices, setIndices] = useState<any[]>([]);
  const [loadingIndices, setLoadingIndices] = useState(false);
  const [topGainers, setTopGainers] = useState<any[]>([]);
  const [loadingGainers, setLoadingGainers] = useState(false);

  useEffect(() => {
    const fetchIndices = async () => {
      setLoadingIndices(true);
      try {
        const res = await api.getMarketIndex();
        if (res.data.status === 'success') {
          setIndices(res.data.data);
        }
      } catch (error) {
        console.error(error);
      } finally {
        setLoadingIndices(false);
      }
    };

    const fetchTopGainers = async () => {
      setLoadingGainers(true);
      try {
        const res = await api.getTopGainers();
        if (res.data.status === 'success') {
          setTopGainers(res.data.data);
        }
      } catch (error) {
        console.error(error);
      } finally {
        setLoadingGainers(false);
      }
    };

    fetchIndices();
    fetchTopGainers();
  }, []);

  return (
    <MainLayout>
        <Row gutter={[16, 16]}>
          <Col xs={24} lg={16}>
            <Card title="市场风向标" variant="borderless">
              {loadingGainers ? <Spin /> : <StockChart data={topGainers} />}
            </Card>
          </Col>
          <Col xs={24} lg={8}>
            <Card title="市场指数" variant="borderless">
              {loadingIndices ? <Spin /> : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
                  {indices.map((index, i) => (
                    <div key={i} style={{ padding: 16, background: isDark ? '#333' : '#f5f5f5', borderRadius: 8 }}>
                       <Statistic
                         title={index.title}
                         value={index.value}
                         precision={2}
                         valueStyle={{ color: index.is_up ? '#cf1322' : '#3f8600' }}
                         prefix={index.is_up ? <ArrowUpOutlined /> : <ArrowDownOutlined />}
                         suffix={`${index.change > 0 ? '+' : ''}${index.change}%`}
                       />
                    </div>
                  ))}
                </div>
              )}
            </Card>
          </Col>
        </Row>
    </MainLayout>
  );
};
