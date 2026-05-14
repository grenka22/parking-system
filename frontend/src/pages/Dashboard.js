import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { zonesAPI, slotsAPI, reservationsAPI } from '../services/api';
import {
  Container,
  Grid,
  Paper,
  Typography,
  Card,
  CardContent,
  Button,
  Box,
  Chip,
  CircularProgress,
  Alert,
} from '@mui/material';

const Dashboard = () => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  
  const [zones, setZones] = useState([]);
  const [availableSlots, setAvailableSlots] = useState([]);
  const [myReservations, setMyReservations] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      setError('');
      setLoading(true);
      
      const [zonesRes, slotsRes, reservationsRes] = await Promise.all([
        zonesAPI.getAll(),
        slotsAPI.getAvailable(),
        reservationsAPI.getMyReservations(),
      ]);

      setZones(zonesRes.data || []);
      setAvailableSlots(slotsRes.data?.slice(0, 6) || []);
      setMyReservations(reservationsRes.data || []);
    } catch (err) {
      console.error('Error fetching data:', err);
      setError('Не удалось загрузить данные. Попробуйте обновить страницу.');
    } finally {
      setLoading(false);
    }
  };

  const getStatusLabel = (status) => {
    const labels = {
      'pending': 'Ожидает',
      'active': 'Активно',
      'completed': 'Завершено',
      'cancelled': 'Отменено',
      'no_show': 'Не явился',
    };
    return labels[status] || status;
  };

  const getStatusColor = (status) => {
    const colors = {
      'pending': 'warning',
      'active': 'success',
      'completed': 'default',
      'cancelled': 'error',
      'no_show': 'error',
    };
    return colors[status] || 'default';
  };

  if (loading) {
    return (
      <Container maxWidth="lg" sx={{ mt: 8, textAlign: 'center' }}>
        <CircularProgress />
        <Typography sx={{ mt: 2 }}>Загрузка...</Typography>
      </Container>
    );
  }

  return (
    <Container maxWidth="lg" sx={{ mt: 4, mb: 4 }}>
      {/* Заголовок */}
      <Typography variant="h4" gutterBottom sx={{ mb: 3 }}>
        Добро пожаловать, {user?.username}!
      </Typography>

      {error && (
        <Alert severity="error" sx={{ mb: 3 }}>
          {error}
        </Alert>
      )}

      {/* Статистика */}
      <Grid container spacing={3} sx={{ mb: 4 }}>
        <Grid item xs={12} sm={4}>
          <Card sx={{ height: '100%' }}>
            <CardContent>
              <Typography color="textSecondary" gutterBottom>
                Всего зон
              </Typography>
              <Typography variant="h3">{zones.length}</Typography>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} sm={4}>
          <Card sx={{ height: '100%' }}>
            <CardContent>
              <Typography color="textSecondary" gutterBottom>
                Свободных мест
              </Typography>
              <Typography variant="h3">{availableSlots.length}</Typography>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} sm={4}>
          <Card sx={{ height: '100%' }}>
            <CardContent>
              <Typography color="textSecondary" gutterBottom>
                Мои брони
              </Typography>
              <Typography variant="h3">{myReservations.length}</Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Зоны парковки */}
      <Grid container spacing={3} sx={{ mb: 4 }}>
        <Grid item xs={12}>
          <Paper sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>
              Зоны парковки
            </Typography>
            {zones.length > 0 ? (
              <Grid container spacing={2}>
                {zones.map((zone) => (
                  <Grid item xs={12} sm={6} md={4} key={zone.id}>
                    <Card>
                      <CardContent>
                        <Typography variant="h6">{zone.name}</Typography>
                        <Typography color="textSecondary" variant="body2">
                          Тип: {zone.zone_type}
                        </Typography>
                        <Typography color="textSecondary" variant="body2">
                          Вместимость: {zone.capacity}
                        </Typography>
                        <Chip
                          label={`${zone.slots_count || 0} мест`}
                          color="primary"
                          size="small"
                          sx={{ mt: 1 }}
                        />
                      </CardContent>
                    </Card>
                  </Grid>
                ))}
              </Grid>
            ) : (
              <Typography color="textSecondary">
                Зоны пока не добавлены
              </Typography>
            )}
          </Paper>
        </Grid>

        {/* Свободные места */}
        <Grid item xs={12}>
          <Paper sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>
              Свободные места
            </Typography>
            {availableSlots.length > 0 ? (
              <Grid container spacing={2}>
                {availableSlots.map((slot) => (
                  <Grid item xs={12} sm={6} md={4} lg={3} key={slot.id}>
                    <Card>
                      <CardContent>
                        <Typography variant="h6">Место {slot.number}</Typography>
                        <Typography color="textSecondary" variant="body2" gutterBottom>
                          Зона: {slot.zone_name || slot.zone?.name || 'Неизвестно'}
                        </Typography>
                        <Button
                          variant="contained"
                          size="small"
                          fullWidth
                          sx={{ mt: 1 }}
                          onClick={() => navigate(`/book/${slot.id}`)}
                        >
                          ЗАБРОНИРОВАТЬ
                        </Button>
                      </CardContent>
                    </Card>
                  </Grid>
                ))}
              </Grid>
            ) : (
              <Typography color="textSecondary">
                Нет доступных мест в данный момент
              </Typography>
            )}
          </Paper>
        </Grid>

        {/* Мои бронирования */}
        <Grid item xs={12}>
          <Paper sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>
              Мои бронирования
            </Typography>
            {myReservations.length > 0 ? (
              <Box>
                {myReservations.map((res) => (
                  <Card key={res.id} sx={{ mb: 2 }}>
                    <CardContent>
                      <Grid container spacing={2} alignItems="center">
                        <Grid item xs={12} md={3}>
                          <Typography variant="subtitle1">
                            <strong>Код:</strong> {res.booking_code}
                          </Typography>
                        </Grid>
                        <Grid item xs={12} md={2}>
                          <Typography>
                            <strong>Место:</strong> {res.slot_number || res.slot?.number}
                          </Typography>
                        </Grid>
                        <Grid item xs={12} md={3}>
                          <Typography variant="body2">
                            {new Date(res.start_time).toLocaleString('ru-RU', {
                              day: '2-digit',
                              month: '2-digit',
                              year: 'numeric',
                              hour: '2-digit',
                              minute: '2-digit',
                            })}
                          </Typography>
                        </Grid>
                        <Grid item xs={12} md={2}>
                          <Chip
                            label={getStatusLabel(res.status)}
                            color={getStatusLabel(res.status) === 'Активно' ? 'success' : 
                                   getStatusLabel(res.status) === 'Ожидает' ? 'warning' :
                                   getStatusLabel(res.status) === 'Отменено' ? 'error' : 'default'}
                            size="small"
                          />
                        </Grid>
                        <Grid item xs={12} md={2}>
                          <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
                            {/* КНОПКА ЗАЯВЛЕНИЯ ОБ УГОНЕ */}
                            <Button
                              size="small"
                              variant="outlined"
                              color="error"
                              onClick={() => navigate(`/theft-report/${res.id}`)}
                              sx={{ 
                                fontSize: '0.75rem',
                                minWidth: 'auto',
                                padding: '4px 8px',
                                borderColor: 'error.main',
                                '&:hover': {
                                  borderColor: 'error.dark',
                                  backgroundColor: 'error.light',
                                  color: 'white',
                                }
                              }}
                            >
                               Угон
                            </Button>
                          </Box>
                        </Grid>
                      </Grid>
                    </CardContent>
                  </Card>
                ))}
              </Box>
            ) : (
              <Typography color="textSecondary">
                У вас нет активных бронирований
              </Typography>
            )}
          </Paper>
        </Grid>
      </Grid>
    </Container>
  );
};

export default Dashboard;