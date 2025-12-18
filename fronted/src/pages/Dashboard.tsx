import { useEffect, useState } from 'react';
import { MainLayout } from '../layout/MainLayout';
import { StockChart } from '../components/StockChart';
import { useStore } from '../store/useStore';
import { Card, Row, Col, Statistic, Spin, Segmented } from 'antd';
import { ArrowUpOutlined, ArrowDownOutlined } from '@ant-design/icons';
import * as api from '../api';

export const Dashboard = () => {
  const { isDark } = useStore();
  const [indices, setIndices] = useState<any[]>([]);
  const [loadingIndices, setLoadingIndices] = useState(false);
  const [topGainers, setTopGainers] = useState<any[]>([]);
  const [loadingGainers, setLoadingGainers] = useState(false);
  const [topIndustries, setTopIndustries] = useState<any[]>([]);
  const [loadingIndustries, setLoadingIndustries] = useState(false);
  const [chartMode, setChartMode] = useState<'stocks' | 'industries'>('stocks');

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

    const fetchTopIndustries = async () => {
      setLoadingIndustries(true);
      try {
        const res = await api.getTopIndustries();
        if (res.data.status === 'success') {
          setTopIndustries(res.data.data);
        }
      } catch (error) {
        console.error(error);
      } finally {
        setLoadingIndustries(false);
      }
    };

    fetchIndices();
    fetchTopGainers();
    fetchTopIndustries();
  }, []);

  return (
    <MainLayout>
        <Row gutter={[16, 16]}>
          <Col xs={24} lg={16}>
            <Card
              title="市场风向标"
              extra={
                <Segmented
                  options={[
                    { label: '涨幅榜', value: 'stocks' },
                    { label: '领涨板块', value: 'industries' },
                  ]}
                  value={chartMode}
                  onChange={(val) => setChartMode(val as 'stocks' | 'industries')}
                />
              }
              variant="borderless"
            >
              {chartMode === 'stocks' ? (
                loadingGainers ? <Spin /> : <StockChart data={topGainers} title="今日涨幅榜 Top 10" />
              ) : (
                loadingIndustries ? <Spin /> : <StockChart data={topIndustries} title="今日领涨板块 Top 10" />
              )}
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
                          suffix={`${index.change > 0 ? '+' : ''}${index.change}% ${typeof index.change_abs !== 'undefined' ? `(${index.change_abs > 0 ? '+' : ''}${index.change_abs})` : ''}`}
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
