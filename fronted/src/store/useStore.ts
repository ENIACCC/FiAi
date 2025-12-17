import { create } from 'zustand';

interface AppState {
  isDark: boolean;
  toggleTheme: () => void;
  watchlist: Set<string>;
  addToWatchlist: (code: string) => void;
  removeFromWatchlist: (code: string) => void;
  setWatchlist: (codes: string[]) => void;
  token: string | null;
  refreshToken: string | null;
  username: string | null;
  setAuth: (token: string, refreshToken: string, username: string) => void;
  logout: () => void;
}

export const useStore = create<AppState>((set) => ({
  isDark: false,
  toggleTheme: () => set((state) => ({ isDark: !state.isDark })),
  watchlist: new Set(),
  addToWatchlist: (code) => set((state) => {
    const newSet = new Set(state.watchlist);
    newSet.add(code);
    return { watchlist: newSet };
  }),
  removeFromWatchlist: (code) => set((state) => {
    const newSet = new Set(state.watchlist);
    newSet.delete(code);
    return { watchlist: newSet };
  }),
  setWatchlist: (codes) => set({ watchlist: new Set(codes) }),
  token: localStorage.getItem('token'),
  refreshToken: localStorage.getItem('refreshToken'),
  username: localStorage.getItem('username'),
  setAuth: (token, refreshToken, username) => {
      localStorage.setItem('token', token);
      localStorage.setItem('refreshToken', refreshToken);
      localStorage.setItem('username', username);
      set({ token, refreshToken, username });
  },
  logout: () => {
      localStorage.removeItem('token');
      localStorage.removeItem('refreshToken');
      localStorage.removeItem('username');
      set({ token: null, refreshToken: null, username: null });
  }
}));
