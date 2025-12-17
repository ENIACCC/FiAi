import { useState, useEffect } from 'react';
import { useStore } from '../store/useStore';
import * as api from '../api';

export const useStockData = () => {
  const { setWatchlist } = useStore();
  const [data, setData] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);

  const fetchData = async (query?: string) => {
    setLoading(true);
    try {
      // Use allSettled or separate try-catch to avoid one failure blocking others
      // Actually, we want stocks even if watchlist fails
      const stockRes = await api.getStocks(query);
      
      let watchlistData: string[] = [];
      try {
        const watchRes = await api.getWatchlist();
        if (watchRes.data.status === 'success') {
           watchlistData = watchRes.data.data.map((item: any) => item.ts_code);
        }
      } catch (e) {
        console.warn('Failed to fetch watchlist:', e);
        // Ignore watchlist error (e.g. 401)
      }

      setData(stockRes.data.data);
      if (watchlistData.length > 0) {
        setWatchlist(watchlistData);
      }
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, [setWatchlist]);

  const search = (query: string) => {
    fetchData(query);
  };

  return { data, loading, search };
};
