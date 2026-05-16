import axios from 'axios';

const API_URL = 'http://130.193.53.192:8000';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: { 'Content-Type': 'application/json' },
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
}, (error) => Promise.reject(error));

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;
    
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;
      
      try {
        const refreshToken = localStorage.getItem('refresh_token');
        if (!refreshToken) throw new Error('No refresh token');
        
        const response = await axios.post(`${API_BASE_URL}/auth/refresh/`, {
          refresh: refreshToken,
        });

        const { access } = response.data;
        localStorage.setItem('access_token', access);
        
        originalRequest.headers.Authorization = `Bearer ${access}`;
        return api(originalRequest);
      } catch (refreshError) {
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        localStorage.removeItem('user');
        window.location.href = '/login';
        return Promise.reject(refreshError);
      }
    }
    
    return Promise.reject(error);
  }
);

export const authAPI = {
  login: (username, password) => 
    api.post('/auth/login/', { username, password }),
  register: (userData) => 
    api.post('/auth/register/', userData),
  getProfile: () => 
    api.get('/auth/profile/'),
  logout: () => {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    localStorage.removeItem('user');
  },
};

export const zonesAPI = {
  getAll: () => api.get('/zones/'),
};

export const slotsAPI = {
  getAll: () => api.get('/slots/'),
  getAvailable: () => api.get('/slots/available/'),
  getById: (id) => api.get(`/slots/${id}/`),
  recommend: (data) => api.post('/slots/recommend/', data),  // ← ДОБАВЬ ЭТО!
};

export const reservationsAPI = {
  getMyReservations: () => api.get('/reservations/my_reservations/'),
  quickBook: (data) => api.post('/reservations/quick_book/', data),
  cancel: (id) => api.post(`/reservations/${id}/cancel/`),
  confirm: (id) => api.post(`/reservations/${id}/confirm_arrival/`),
};

export const theftAPI = {
  create: (data) => api.post('/theft-reports/', data),
  getMyReports: () => api.get('/theft-reports/my_reports/'),
};

export default api;