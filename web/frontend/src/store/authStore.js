import { create } from 'zustand'

const TOKEN_KEY = 'mc_token'

export const useAuthStore = create((set) => ({
  user: null,
  token: localStorage.getItem(TOKEN_KEY) || null,

  setAuth: (user, token) => {
    localStorage.setItem(TOKEN_KEY, token)
    set({ user, token })
  },

  logout: () => {
    localStorage.removeItem(TOKEN_KEY)
    set({ user: null, token: null })
  },
}))
