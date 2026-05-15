import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Container,
  Box,
  Typography,
  TextField,
  Button,
  Paper,
  Alert,
  CircularProgress,
  Grid,
  Card,
  CardContent,
  Chip,
} from '@mui/material';
import { Star, AutoAwesome, Event, AccessTime } from '@mui/icons-material';
import { slotsAPI, reservationsAPI } from '../services/api';
import CarPlates from '../components/CarPlates';

const Booking = () => {
  const { slotId } = useParams();
  const navigate = useNavigate();
  
  const [slot, setSlot] = useState(null);
  const [loading, setLoading] = useState(true);
  const [bookingLoading, setBookingLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  
  const [formData, setFormData] = useState({
    start_time: '',
    end_time: '',
    user_name: '',
    user_phone: '',
    user_email: '',
  });
  
  const [licensePlate, setLicensePlate] = useState('');
  const [showRecommendations, setShowRecommendations] = useState(false);
  const [recommendations, setRecommendations] = useState([]);
  const [recommendLoading, setRecommendLoading] = useState(false);

  useEffect(() => {
    fetchSlotData();
  }, [slotId]);

  const fetchSlotData = async () => {
    try {
      setLoading(true);
      const response = await slotsAPI.getById(slotId);
      setSlot(response.data);
      
      const userData = JSON.parse(localStorage.getItem('user') || '{}');
      setFormData(prev => ({
        ...prev,
        user_name: userData.username || '',
        user_email: userData.email || '',
        user_phone: userData.phone || '',
      }));
    } catch (err) {
      console.error('Error fetching slot:', err);
      setError('Не удалось загрузить информацию о месте');
    } finally {
      setLoading(false);
    }
  };

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
  };

  const handleGetRecommendations = async () => {
    if (!formData.start_time || !formData.end_time) {
      setError('Сначала укажите время бронирования');
      return;
    }

    setRecommendLoading(true);
    setError('');
    setShowRecommendations(true);

    try {
      const response = await slotsAPI.recommend({
        start_time: new Date(formData.start_time).toISOString(),
        end_time: new Date(formData.end_time).toISOString(),
      });

      if (response.data.success) {
        setRecommendations(response.data.recommendations || []);
      } else {
        setError(response.data.message || 'Нет доступных мест');
        setRecommendations([]);
      }
    } catch (err) {
      console.error('Recommendation error:', err);
      setError(err.response?.data?.error || 'Ошибка при получении рекомендаций');
      setRecommendations([]);
    } finally {
      setRecommendLoading(false);
    }
  };

  const handleSelectRecommendedSlot = (recommendedSlotId) => {
    if (recommendedSlotId === parseInt(slotId)) {
      setShowRecommendations(false);
      return;
    }
    navigate(`/book/${recommendedSlotId}`);
  };

  const formatDateTime = (dateString) => {
    if (!dateString) return '';
    const date = new Date(dateString);
    return date.toISOString().slice(0, 19);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setSuccess('');
    setBookingLoading(true);

    try {
      const token = localStorage.getItem('access_token');
      const isGuestBooking = !token;

      const plateClean = licensePlate ? licensePlate.replace(/[\s-]/g, '') : '';
      if (!licensePlate || plateClean.length < 6) {
        throw new Error('Введите корректный номер автомобиля');
      }

      if (!formData.start_time || !formData.end_time) {
        throw new Error('Укажите время начала и окончания');
      }

      const start = new Date(formData.start_time);
      const end = new Date(formData.end_time);
      
      if (isNaN(start.getTime()) || isNaN(end.getTime())) {
        throw new Error('Неверный формат даты');
      }
      
      if (end <= start) {
        throw new Error('Время окончания должно быть позже времени начала');
      }

      const duration = (end - start) / (1000 * 60 * 60);
      if (duration > 3) {
        throw new Error('Максимальное время бронирования — 3 часа');
      }

      const now = new Date();
      if (start.getTime() < (now.getTime() - 120000)) {
        throw new Error('Время начала должно быть в будущем');
      }

      const bookingData = {
        slot_id: parseInt(slotId),
        start_time: formatDateTime(formData.start_time),
        end_time: formatDateTime(formData.end_time),
        is_guest: isGuestBooking,
        license_plate: licensePlate,
      };

      if (isGuestBooking) {
        if (!formData.user_name || !formData.user_phone || !formData.user_email) {
          throw new Error('Заполните все контактные данные');
        }
        bookingData.guest_name = formData.user_name;
        bookingData.guest_phone = formData.user_phone;
        bookingData.guest_email = formData.user_email;
      }

      const response = await reservationsAPI.quickBook(bookingData);
      setSuccess(` Бронирование успешно! Код: ${response.data.booking_code}`);
      
      setTimeout(() => {
        navigate('/dashboard');
      }, 2000);
      
    } catch (err) {
      console.error('Booking error:', err);
      setError(err.response?.data?.error || err.message || 'Ошибка при создании брони');
    } finally {
      setBookingLoading(false);
    }
  };

  if (loading) {
    return (
      <Container maxWidth="md" sx={{ mt: 8, textAlign: 'center' }}>
        <CircularProgress />
        <Typography sx={{ mt: 2 }}>Загрузка информации о месте...</Typography>
      </Container>
    );
  }

  if (!slot) {
    return (
      <Container maxWidth="md" sx={{ mt: 8 }}>
        <Alert severity="error">Место не найдено</Alert>
        <Button variant="outlined" onClick={() => navigate('/dashboard')} sx={{ mt: 2 }}>
          Назад
        </Button>
      </Container>
    );
  }

  return (
    <Container component="main" maxWidth="md">
      <Box sx={{ marginTop: 8, marginBottom: 4 }}>
        <Paper elevation={3} sx={{ p: 4 }}>
          <Typography component="h1" variant="h5" gutterBottom>
             Бронирование места
          </Typography>
          
          <Card variant="outlined" sx={{ mb: 3, bgcolor: '#f5f5f5' }}>
            <CardContent>
              <Grid container spacing={2} alignItems="center">
                <Grid item xs={12} sm={6}>
                  <Typography variant="h6">
                    Место {slot.number}
                  </Typography>
                  <Typography color="textSecondary">
                    Зона: {slot.zone_name || slot.zone?.name || 'Неизвестно'}
                  </Typography>
                </Grid>
                <Grid item xs={12} sm={6}>
                  <Chip 
                    label={slot.is_active ? 'Активно' : 'Неактивно'} 
                    color={slot.is_active ? 'success' : 'default'}
                  />
                  {slot.zone_type && (
                    <Chip label={slot.zone_type} size="small" sx={{ ml: 1 }} />
                  )}
                </Grid>
              </Grid>
            </CardContent>
          </Card>

          <Alert severity="info" sx={{ mb: 3 }}>
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <AutoAwesome sx={{ color: '#1976d2' }} />
                <Typography variant="body2" fontWeight="bold">
                   Умный подбор места
                </Typography>
              </Box>
              
              <Typography variant="body2" color="textSecondary">
                Не уверены в выборе? Наш алгоритм подберет лучшее место!
              </Typography>
              
              <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap' }}>
                <Button
                  variant="outlined"
                  size="small"
                  onClick={handleGetRecommendations}
                  disabled={recommendLoading || !formData.start_time || !formData.end_time}
                  startIcon={recommendLoading ? <CircularProgress size={16} /> : <Star />}
                >
                  {recommendLoading ? 'Подбираем...' : 'Подобрать лучшее место'}
                </Button>
                
                {recommendations.length > 0 && (
                  <Button
                    variant="text"
                    size="small"
                    onClick={() => setShowRecommendations(!showRecommendations)}
                  >
                    {showRecommendations ? 'Скрыть' : 'Показать рекомендации'}
                  </Button>
                )}
              </Box>

              {showRecommendations && recommendations.length > 0 && (
                <Box sx={{ mt: 2 }}>
                  <Typography variant="subtitle2" gutterBottom>
                    Рекомендуемые места:
                  </Typography>
                  
                  {recommendations.map((rec) => (
                    <Card
                      key={rec.slot_id}
                      sx={{
                        mb: 1,
                        cursor: 'pointer',
                        border: slotId === rec.slot_id.toString() 
                          ? '2px solid #1976d2' 
                          : '1px solid #e0e0e0',
                        bgcolor: slotId === rec.slot_id.toString() ? '#e3f2fd' : 'inherit',
                        transition: 'all 0.2s',
                        '&:hover': {
                          bgcolor: '#f5f5f5',
                          transform: 'translateX(4px)',
                        }
                      }}
                      onClick={() => handleSelectRecommendedSlot(rec.slot_id)}
                    >
                      <CardContent sx={{ py: 1, px: 2 }}>
                        <Grid container spacing={1} alignItems="center">
                          <Grid item xs={3} sm={2}>
                            <Typography variant="body2" fontWeight="bold">
                              {rec.rank_icon} #{rec.slot_number}
                            </Typography>
                          </Grid>
                          <Grid item xs={4} sm={3}>
                            <Chip label={rec.zone_name} size="small" variant="outlined" />
                          </Grid>
                          <Grid item xs={3} sm={3}>
                            <Typography variant="caption" color="textSecondary">
                              {rec.zone_load_percent}%
                            </Typography>
                          </Grid>
                          <Grid item xs={2} sm={4}>
                            <Typography variant="caption" color="textSecondary">
                              Score: {rec.score}
                            </Typography>
                          </Grid>
                        </Grid>
                        <Typography variant="caption" color="textSecondary" sx={{ mt: 0.5, display: 'block' }}>
                            {rec.reason_text}
                        </Typography>
                      </CardContent>
                    </Card>
                  ))}
                </Box>
              )}
            </Box>
          </Alert>

          {error && (
            <Alert severity="error" sx={{ mb: 2, mt: 2 }}>
              {error}
            </Alert>
          )}

          {success && (
            <Alert severity="success" sx={{ mb: 2, mt: 2 }}>
              {success}
            </Alert>
          )}

          <Box component="form" onSubmit={handleSubmit} sx={{ mt: 3 }}>
            <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              <Event /> Время бронирования
            </Typography>
            
            <Grid container spacing={2}>
              <Grid item xs={12} sm={6}>
                <Typography variant="body2" color="textSecondary" sx={{ mb: 0.5 }}>Время начала *</Typography>
                <TextField
                  required
                  fullWidth
                  
                  type="datetime-local"
                  name="start_time"
                  value={formData.start_time}
                  onChange={handleChange}
                  InputLabelProps={{ 
                    shrink: true,
                    sx: {
                      backgroundColor: 'white',
                      px: 0.5,
                      fontSize: '12px',
                    }
                  }}
                  InputProps={{
                    sx: {
                      fontSize: '14px',
                      minHeight: '56px',
                    }
                  }}
                  variant="outlined"
                  size="medium"
                />
              </Grid>
              
              <Grid item xs={12} sm={6}>
                <Typography variant="body2" color="textSecondary" sx={{ mb: 0.5 }}>Время окончания *</Typography>
                <TextField
                  required
                  fullWidth
                  
                  type="datetime-local"
                  name="end_time"
                  value={formData.end_time}
                  onChange={handleChange}
                  InputLabelProps={{ 
                    shrink: true,
                    sx: {
                      backgroundColor: 'white',
                      px: 0.5,
                      fontSize: '12px',
                    }
                  }}
                  InputProps={{
                    sx: {
                      fontSize: '14px',
                      minHeight: '56px',
                    }
                  }}
                  variant="outlined"
                  size="medium"
                />
              </Grid>
            </Grid>

            <Alert severity="info" sx={{ mt: 2, mb: 2 }}>
               Максимальное время бронирования — 3 часа
            </Alert>

            <Typography variant="h6" gutterBottom sx={{ mt: 3 }}>
               Информация об автомобиле
            </Typography>
            
            <CarPlates
              value={licensePlate}
              onChange={setLicensePlate}
              error={!!error && !licensePlate}
              helperText="Введите номер автомобиля для бронирования"
            />

            {!localStorage.getItem('access_token') && (
              <>
                <Typography variant="h6" gutterBottom sx={{ mt: 3 }}>
                   Контактная информация
                </Typography>
                
                <TextField
                  required
                  fullWidth
                  label="Имя"
                  name="user_name"
                  value={formData.user_name}
                  onChange={handleChange}
                  variant="outlined"
                  size="medium"
                  sx={{ mb: 2 }}
                />

                <Grid container spacing={2}>
                  <Grid item xs={12} sm={6}>
                    <TextField
                      required
                      fullWidth
                      label="Телефон"
                      name="user_phone"
                      value={formData.user_phone}
                      onChange={handleChange}
                      variant="outlined"
                      size="medium"
                    />
                  </Grid>
                  
                  <Grid item xs={12} sm={6}>
                    <TextField
                      required
                      fullWidth
                      label="Email"
                      name="user_email"
                      type="email"
                      value={formData.user_email}
                      onChange={handleChange}
                      variant="outlined"
                      size="medium"
                    />
                  </Grid>
                </Grid>
              </>
            )}

            <Box sx={{ display: 'flex', gap: 2, mt: 4 }}>
              <Button
                type="submit"
                variant="contained"
                size="large"
                disabled={bookingLoading}
                sx={{ flex: 1 }}
              >
                {bookingLoading ? <CircularProgress size={24} /> : 'ЗАБРОНИРОВАТЬ'}
              </Button>
              
              <Button
                variant="outlined"
                size="large"
                onClick={() => navigate('/dashboard')}
                disabled={bookingLoading}
              >
                ОТМЕНА
              </Button>
            </Box>

            <Alert severity="warning" sx={{ mt: 3 }}>
               Один пользователь может иметь максимум 3 активных бронирования
            </Alert>
          </Box>
        </Paper>
      </Box>
    </Container>
  );
};

export default Booking;