import axios from 'axios';

const api = axios.create({
  baseURL: 'http://127.0.0.1:8000/api/',
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
export const getWatchlist = () => api.get('watchlist/');
export const addToWatchlist = (data: { ts_code: string; name: string }) => api.post('watchlist/', data);
export const removeFromWatchlist = (ts_code: string) => api.delete(`watchlist/?ts_code=${ts_code}`);
export const analyzeWatchlist = () => api.post('ai/analyze/');

export default api;
