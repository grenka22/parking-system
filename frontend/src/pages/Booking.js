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
} from '@mui/material';
import { slotsAPI, reservationsAPI } from '../services/api';

// ✅ ВСЁ ВНУТРИ КОМПОНЕНТА!
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

  useEffect(() => {
    fetchSlotData();
  }, [slotId]);

  const fetchSlotData = async () => {
    try {
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
      console.error('Error:', err);
      setError('Не удалось загрузить информацию о месте');
    } finally {
      setLoading(false);
    }
  };

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value,
    }));
  };

  const formatDateTime = (dateString) => {
    if (!dateString) return '';
    return new Date(dateString).toISOString().slice(0, 19);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setSuccess('');
    setBookingLoading(true);

    try {
      const bookingData = {
        slot_id: parseInt(slotId),
        start_time: formatDateTime(formData.start_time),
        end_time: formatDateTime(formData.end_time),
        user_name: formData.user_name,
        user_phone: formData.user_phone,
        user_email: formData.user_email,
        is_guest: true,
      };

      if (!bookingData.start_time || !bookingData.end_time) {
        throw new Error('Укажите время начала и окончания');
      }

      const start = new Date(bookingData.start_time);
      const end = new Date(bookingData.end_time);
      
      if (end <= start) {
        throw new Error('Время окончания должно быть позже');
      }

      const response = await reservationsAPI.quickBook(bookingData);
      
      setSuccess(`✅ Бронирование успешно! Код: ${response.data.booking_code}`);
      
      setTimeout(() => {
        navigate('/dashboard');
      }, 2000);
      
    } catch (err) {
      console.error('Booking error:', err);
      setError(err.response?.data?.error || 'Ошибка при создании брони');
    } finally {
      setBookingLoading(false);
    }
  };

  if (loading) {
    return (
      <Container maxWidth="md" sx={{ mt: 8, textAlign: 'center' }}>
        <CircularProgress />
      </Container>
    );
  }

  if (!slot) {
    return (
      <Container maxWidth="md" sx={{ mt: 8 }}>
        <Alert severity="error">Место не найдено</Alert>
        <Button 
          variant="outlined" 
          onClick={() => navigate('/dashboard')} 
          sx={{ mt: 2 }}
        >
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
            🅿️ Бронирование места
          </Typography>
          
          <Typography variant="h6" color="text.secondary" gutterBottom>
            {slot.number}
          </Typography>
          <Typography variant="body1" color="text.secondary" gutterBottom>
            Зона: {slot.zone?.name || 'Неизвестно'}
          </Typography>

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
            <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap' }}>
              <TextField
                margin="normal"
                required
                fullWidth
                label="Время начала *"
                type="datetime-local"
                name="start_time"
                value={formData.start_time}
                onChange={handleChange}
                InputLabelProps={{ shrink: true }}
                sx={{ flex: 1, minWidth: 200 }}
              />
              
              <TextField
                margin="normal"
                required
                fullWidth
                label="Время окончания *"
                type="datetime-local"
                name="end_time"
                value={formData.end_time}
                onChange={handleChange}
                InputLabelProps={{ shrink: true }}
                sx={{ flex: 1, minWidth: 200 }}
              />
            </Box>

            <TextField
              margin="normal"
              required
              fullWidth
              label="Имя *"
              name="user_name"
              value={formData.user_name}
              onChange={handleChange}
            />

            <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap' }}>
              <TextField
                margin="normal"
                required
                fullWidth
                label="Телефон *"
                name="user_phone"
                value={formData.user_phone}
                onChange={handleChange}
                sx={{ flex: 1, minWidth: 200 }}
              />
              
              <TextField
                margin="normal"
                required
                fullWidth
                label="Email *"
                name="user_email"
                type="email"
                value={formData.user_email}
                onChange={handleChange}
                sx={{ flex: 1, minWidth: 200 }}
              />
            </Box>

            <Box sx={{ display: 'flex', gap: 2, mt: 3 }}>
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
          </Box>
        </Paper>
      </Box>
    </Container>
  );
};

export default Booking;