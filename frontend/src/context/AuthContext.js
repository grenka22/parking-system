import React, { createContext, useState, useContext, useEffect } from 'react';
import { authAPI } from '../services/api';

const AuthContext = createContext(null);

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  // При загрузке проверяем, есть ли сохранённая сессия
  useEffect(() => {
    const storedUser = localStorage.getItem('user');
    const token = localStorage.getItem('access');
    if (storedUser && token) {
      setUser(JSON.parse(storedUser));
    }
    setLoading(false);
  }, []);

  const login = async (username, password) => {
    const response = await authAPI.login(username, password);
    // SimpleJWT возвращает поля 'access' и 'refresh'
    localStorage.setItem('access', response.data.access);
    localStorage.setItem('refresh', response.data.refresh);
    
    const userData = { username };
    localStorage.setItem('user', JSON.stringify(userData));
    setUser(userData);
    return response.data;
  };

  const register = async (formData) => {
    // Убираем password_confirm перед отправкой на бэкенд
    const { password_confirm, ...dataToSend } = formData;
    const response = await authAPI.register(dataToSend);
    
    // После успешной регистрации сразу авторизуем
    await login(formData.username, formData.password);
    return response.data;
  };

  const logout = () => {
    authAPI.logout();
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, login, register, logout, loading }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) throw new Error('useAuth must be used within AuthProvider');
  return context;
};