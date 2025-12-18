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

export const login = (data: any) => api.post('token/', data);
export const register = (data: any) => api.post('register/', data);
export const getStocks = (q?: string) => api.get('stock/', { params: { q } });
export const getMarketIndex = () => api.get('market/index/');
export const getTopGainers = () => api.get('market/top-gainers/');
export const getTopIndustries = () => api.get('market/top-industries/');

// Watchlist Groups
export const getWatchlistGroups = () => api.get('watchlist-groups/');
export const createWatchlistGroup = (name: string) => api.post('watchlist-groups/', { name });
export const deleteWatchlistGroup = (id: string) => api.delete(`watchlist-groups/${id}/`);

// Watchlist Items
export const getWatchlist = (group_id?: string) => api.get('watchlist/', { params: { group_id } });
export const addToWatchlist = (data: { ts_code: string; name: string; group_id?: string }) => api.post('watchlist/', data);
export const removeFromWatchlist = (ts_code: string, group_id?: string) => api.delete(`watchlist/`, { params: { ts_code, group_id } });

export const analyzeWatchlist = () => api.post('ai/analyze/');

export default api;
