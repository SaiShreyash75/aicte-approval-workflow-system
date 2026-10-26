import React, { createContext, useContext, useState, useEffect } from 'react';
import api from '../api/client';

const AuthContext = createContext(null);

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(() => {
    const saved = localStorage.getItem('aicte_user');
    return saved ? JSON.parse(saved) : null;
  });
  const [systemTime, setSystemTime] = useState(null);
  const [refreshKey, setRefreshKey] = useState(0);

  const fetchClock = async () => {
    try {
      const res = await api.get('/admin/time');
      setSystemTime(res.data);
    } catch (e) {
      console.error("Could not fetch clock", e);
    }
  };

  useEffect(() => {
    fetchClock();
  }, [refreshKey]);

  const triggerGlobalRefresh = () => {
    setRefreshKey((prev) => prev + 1);
  };

  const login = async (email, password) => {
    const res = await api.post('/auth/login', { email, password });
    const { access_token, ...userData } = res.data;
    localStorage.setItem('aicte_token', access_token);
    localStorage.setItem('aicte_user', JSON.stringify(userData));
    setUser(userData);
    triggerGlobalRefresh();
    return userData;
  };

  const logout = () => {
    localStorage.removeItem('aicte_token');
    localStorage.removeItem('aicte_user');
    setUser(null);
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        systemTime,
        login,
        logout,
        refreshClock: fetchClock,
        refreshKey,
        triggerGlobalRefresh,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => useContext(AuthContext);
