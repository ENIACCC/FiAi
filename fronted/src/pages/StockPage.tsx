import { MainLayout } from '../layout/MainLayout';
import { StockList } from '../components/StockList';
import { Card } from 'antd';
import { useStockData } from '../hooks/useStockData';

export const StockPage = () => {
  const { data, loading, search } = useStockData();

  return (
    <MainLayout>
      <Card title="股票数据" variant="borderless">
        <StockList data={data} loading={loading} onSearch={search} />
      </Card>
    </MainLayout>
  );
};
