import axios from 'axios'

const API_BASE_URL = "http://localhost:8000/api"

const api = axios.create({
    baseURL: API_BASE_URL,
    headers: {
        'Content-Type' : 'application/json',
    },
});

api.interceptors.request.use(
    (config) => {
        const token = localStorage.getItem('access_token');
        if (token) {
            config.headers.Authorization = `Bearer ${token}`;
        }
        return config;
    },
    (error) => Promise.reject(error)

);

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    if (error.response.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;

      try {
        const refreshToken = localStorage.getItem('refresh_token');
        const response = await axios.post(`${API_BASE_URL}/auth/refresh/`, {
          refresh_token: refreshToken,
        });

        const { access_token } = response.data;
        localStorage.setItem('access_token', access_token);

        originalRequest.headers.Authorization = `Bearer ${access_token}`;
        return api(originalRequest);
      } catch (refreshError) {
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        window.location.href = '/login';
        return Promise.reject(refreshError);
      }
    }

    return Promise.reject(error);
  }
);


export const authAPI = {
    login: (username, password) =>
        api.post('/auth/login/', {username,password}),
    register: (userData) =>
        api.post('/auth/register/', userData),
  
    logout: (refreshToken) =>
        api.post('/auth/logout/', { refresh_token: refreshToken }),
  
    getProfile: () =>
        api.get('/auth/profile/'),
};

export const zonesAPI = {
  getAll: () => api.get('/zones/'),
  getById: (id) => api.get(`/zones/${id}/`),
  getAvailability: () => api.get('/zones/availability/'),
  getRecommendations: () => api.get('/zones/recommendations/'),
};

export const slotsAPI = {
  getAll: () => api.get('/slots/'),
  getAvailable: () => api.get('/slots/available/'),
  getLeastLoaded: () => api.get('/slots/least_loaded/'),
  getMap: () => api.get('/slots/map/'),
  checkAvailability: (id, startTime, endTime) =>
    api.post(`/slots/${id}/check_availability/`, {
      start_time: startTime,
      end_time: endTime,
    }),
};

export const reservationsAPI = {
  getAll: () => api.get('/reservations/'),
  getActive: () => api.get('/reservations/active/'),
  getMyReservations: (email, phone) =>
    api.get('/reservations/my_reservations/', {
      params: { email, phone },
    }),
  quickBook: (data) => api.post('/reservations/quick_book/', data),
  cancel: (id) => api.post(`/reservations/${id}/cancel/`),
  confirm: (id) => api.post(`/reservations/${id}/confirm/`),
  getStatistics: () => api.get('/reservations/statistics/'),
};

export const predictionsAPI = {
  getAvailability: (zoneId, targetTime) =>
    api.get('/predictions/availability/', {
      params: { zone_id: zoneId, target_time: targetTime },
    }),
  getRecommendations: (limit = 5, targetTime) =>
    api.get('/predictions/recommendations/', {
      params: { limit, target_time: targetTime },
    }),
};

export default api;