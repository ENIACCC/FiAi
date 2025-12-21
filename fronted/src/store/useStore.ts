import { create } from 'zustand';

interface AppState {
  isDark: boolean;
  toggleTheme: () => void;
  watchlist: Set<string>;
  addToWatchlist: (code: string) => void;
  removeFromWatchlist: (code: string) => void;
  setWatchlist: (codes: string[]) => void;
  activeGroupId: string;
  setActiveGroupId: (id: string) => void;
  token: string | null;
  refreshToken: string | null;
  username: string | null;
  setAuth: (token: string, refreshToken: string, username: string) => void;
  logout: () => void;
  isAiChatOpen: boolean;
  setAiChatOpen: (isOpen: boolean) => void;
  aiContext: { type: 'stock' | 'general'; data?: any; message?: string } | null;
  setAiContext: (context: { type: 'stock' | 'general'; data?: any; message?: string } | null) => void;
}

export const useStore = create<AppState>((set) => ({
  isDark: false,
  toggleTheme: () => set((state) => ({ isDark: !state.isDark })),
  isAiChatOpen: false,
  setAiChatOpen: (isOpen) => set({ isAiChatOpen: isOpen }),
  aiContext: null,
  setAiContext: (context) => set({ aiContext: context }),
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
  activeGroupId: 'default',
  setActiveGroupId: (id) => set({ activeGroupId: id }),
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
