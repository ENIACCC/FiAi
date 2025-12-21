import axios from 'axios';

const api = axios.create({
  baseURL: '/api/',
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (resp) => resp,
  (error) => {
    const status = error?.response?.status;
    if (status === 401 || status === 403) {
      localStorage.removeItem('token');
      localStorage.removeItem('refreshToken');
      localStorage.removeItem('username');
      if (window.location.pathname !== '/login') {
        window.location.href = '/login';
      }
    }
    return Promise.reject(error);
  },
);

export const login = (data: any) => api.post('token/', data);
export const register = (data: any) => api.post('register/', data);
export const getStocks = (q?: string) => api.get('stock/', { params: { q } });
export const getMarketIndex = () => api.get('market/index/');
export const getTopGainers = () => api.get('market/top-gainers/');
export const getTopIndustries = () => api.get('market/top-industries/');

// Watchlist Groups
export const getWatchlistGroups = () => api.get('watchlist-groups/');
export const createWatchlistGroup = (name: string) => api.post('watchlist-groups/', { name });
export const updateWatchlistGroup = (id: string, name: string) => api.patch(`watchlist-groups/${id}/`, { name });
export const deleteWatchlistGroup = (id: string) => api.delete(`watchlist-groups/${id}/`);
export const getWatchlistCount = () => api.get('watchlist/count/');

// Watchlist Items
export const getWatchlist = (group_id?: string) => api.get('watchlist/', { params: { group_id } });
export const addToWatchlist = (data: { ts_code: string; name: string; group_id?: string }) => api.post('watchlist/', data);
export const removeFromWatchlist = (ts_code: string, group_id?: string) => api.delete(`watchlist/`, { params: { ts_code, group_id } });

export const analyzeWatchlist = (group_id?: string) => api.post('ai/analyze/', { group_id });
export const chatAI = (data: { messages: Array<{ role: string; content: string }>; stock?: any }) => api.post('ai/chat/', data);

export const getEvents = (params: { symbol: string; start?: string; end?: string }) =>
  api.get('events/', { params });

export const getSignals = (params: { symbol: string }) => api.get('signals/', { params });

export const runBacktest = (data: {
  symbol: string;
  template: string;
  params: Record<string, any>;
  start_date?: string;
  end_date?: string;
  oos_start_date?: string;
  initial_cash?: number;
  commission_rate?: number;
  stamp_duty_rate?: number;
  slippage_bps?: number;
  lot_size?: number;
}) => api.post('backtest/', data);

export default api;
