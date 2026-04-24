import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Container,
  Paper,
  Typography,
  TextField,
  Button,
  Grid,
  Box,
  Alert,
} from '@mui/material';
import { slotsAPI, reservationsAPI } from '../services/api';
import { useAuth } from '../context/AuthContext';

const Booking = () => {
  const { slotId } = useParams();
  const navigate = useNavigate();
  const { user } = useAuth();

  const [slot, setSlot] = useState(null);
  const [formData, setFormData] = useState({
    start_time: '',
    end_time: '',
    user_name: user?.username || '',
    user_phone: '',
    user_email: user?.email || '',
    is_guest: false,
  });
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    fetchSlot();
  }, [slotId]);

  const fetchSlot = async () => {
    try {
      const response = await slotsAPI.getAll();
      const foundSlot = response.data.find((s) => s.id === parseInt(slotId));
      setSlot(foundSlot);
    } catch (error) {
      console.error('Error fetching slot:', error);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      await reservationsAPI.quickBook({
        slot_id: parseInt(slotId),
        ...formData,
      });
      alert('Бронирование успешно создано!');
      navigate('/dashboard');
    } catch (err) {
      setError(err.response?.data?.error || 'Ошибка при создании брони');
    } finally {
      setLoading(false);
    }
  };

  if (!slot) return <Typography>Загрузка...</Typography>;

  return (
    <Container maxWidth="md" sx={{ mt: 4 }}>
      <Paper sx={{ p: 4 }}>
        <Typography variant="h5" gutterBottom>
          🅿️ Бронирование места
        </Typography>

        <Box sx={{ mb: 3 }}>
          <Typography variant="h6">Место {slot.number}</Typography>
          <Typography color="textSecondary">Зона: {slot.zone_name}</Typography>
        </Box>

        {error && (
          <Alert severity="error" sx={{ mb: 3 }}>
            {error}
          </Alert>
        )}

        <Box component="form" onSubmit={handleSubmit}>
          <Grid container spacing={3}>
            <Grid item xs={12} md={6}>
              <TextField
                required
                fullWidth
                label="Время начала"
                type="datetime-local"
                value={formData.start_time}
                onChange={(e) =>
                  setFormData({ ...formData, start_time: e.target.value })
                }
                InputLabelProps={{ shrink: true }}
              />
            </Grid>

            <Grid item xs={12} md={6}>
              <TextField
                required
                fullWidth
                label="Время окончания"
                type="datetime-local"
                value={formData.end_time}
                onChange={(e) =>
                  setFormData({ ...formData, end_time: e.target.value })
                }
                InputLabelProps={{ shrink: true }}
              />
            </Grid>

            <Grid item xs={12} md={6}>
              <TextField
                required
                fullWidth
                label="Имя"
                value={formData.user_name}
                onChange={(e) =>
                  setFormData({ ...formData, user_name: e.target.value })
                }
              />
            </Grid>

            <Grid item xs={12} md={6}>
              <TextField
                required
                fullWidth
                label="Телефон"
                value={formData.user_phone}
                onChange={(e) =>
                  setFormData({ ...formData, user_phone: e.target.value })
                }
                placeholder="+79991234567"
              />
            </Grid>

            <Grid item xs={12} md={6}>
              <TextField
                fullWidth
                label="Email"
                type="email"
                value={formData.user_email}
                onChange={(e) =>
                  setFormData({ ...formData, user_email: e.target.value })
                }
              />
            </Grid>
          </Grid>

          <Box sx={{ mt: 3 }}>
            <Button
              type="submit"
              variant="contained"
              size="large"
              disabled={loading}
            >
              {loading ? 'Бронирование...' : 'Забронировать'}
            </Button>
            <Button
              onClick={() => navigate('/dashboard')}
              sx={{ ml: 2 }}
            >
              Отмена
            </Button>
          </Box>
        </Box>
      </Paper>
    </Container>
  );
};

export default Booking;