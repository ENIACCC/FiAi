import { useState, useEffect } from 'react';
import { useStore } from '../store/useStore';
import * as api from '../api';

export const useStockData = () => {
  const { setWatchlist } = useStore();
  const [data, setData] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const fetchData = async () => {
      setLoading(true);
      try {
        const [stockRes, watchRes] = await Promise.all([
          api.getStocks(),
          api.getWatchlist()
        ]);
        setData(stockRes.data.data);
        if (watchRes.data.status === 'success') {
          setWatchlist(watchRes.data.data.map((item: any) => item.ts_code));
        }
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, [setWatchlist]);

  return { data, loading };
};
