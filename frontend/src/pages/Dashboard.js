import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Container,
  Box,
  Typography,
  Paper,
  Grid,
  Card,
  CardContent,
  Button,
  Chip,
  Alert,
  CircularProgress,
  Tooltip,
  Avatar,
  Fab,
} from '@mui/material';
import {
  Videocam,
  CheckCircle,
  Cancel,
  Warning,
  Star,
  Event,
  AccessTime,
  CarCrash,
  Add,
  LocalParking,
} from '@mui/icons-material';
import { reservationsAPI } from '../services/api';

const Dashboard = () => {
  const navigate = useNavigate();
  const [reservations, setReservations] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  useEffect(() => {
    fetchReservations();
  }, []);

  const fetchReservations = async () => {
    try {
      setLoading(true);
      const response = await reservationsAPI.getMyReservations();
      setReservations(response.data);
    } catch (err) {
      console.error('Error fetching reservations:', err);
      setError('Не удалось загрузить бронирования');
    } finally {
      setLoading(false);
    }
  };

  const handleConfirm = async (id) => {
    try {
      await reservationsAPI.confirm(id);
      setSuccess(' Бронирование подтверждено!');
      fetchReservations();
      setTimeout(() => setSuccess(''), 3000);
    } catch (err) {
      setError(err.response?.data?.error || 'Ошибка при подтверждении');
      setTimeout(() => setError(''), 3000);
    }
  };

  const handleCancel = async (id) => {
    if (window.confirm('Вы уверены что хотите отменить бронирование?')) {
      try {
        await reservationsAPI.cancel(id);
        setSuccess(' Бронирование отменено');
        fetchReservations();
        setTimeout(() => setSuccess(''), 3000);
      } catch (err) {
        setError(err.response?.data?.error || 'Ошибка при отмене');
        setTimeout(() => setError(''), 3000);
      }
    }
  };

  const getStatusChip = (status) => {
    const statusConfig = {
      pending: { label: 'Ожидает', color: 'warning', icon: <AccessTime /> },
      active: { label: 'Активно', color: 'success', icon: <CheckCircle /> },
      completed: { label: 'Завершено', color: 'info', icon: <Star /> },
      cancelled: { label: 'Отменено', color: 'error', icon: <Cancel /> },
      no_show: { label: 'Не явился', color: 'default', icon: <Warning /> },
    };

    const config = statusConfig[status] || statusConfig.pending;
    return (
      <Chip
        icon={config.icon}
        label={config.label}
        color={config.color}
        size="small"
      />
    );
  };

  const formatDate = (dateString) => {
    const date = new Date(dateString);
    return date.toLocaleString('ru-RU', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const canCancel = (status) => {
    return status === 'pending' || status === 'active';
  };

  const canConfirm = (status) => {
    return status === 'pending';
  };

  if (loading) {
    return (
      <Container maxWidth="lg" sx={{ mt: 8, textAlign: 'center' }}>
        <CircularProgress />
        <Typography sx={{ mt: 2 }}>Загрузка бронирований...</Typography>
      </Container>
    );
  }

  return (
    <Container maxWidth="lg" sx={{ mt: 8, mb: 4 }}>
      <Box sx={{ 
        display: 'flex', 
        justifyContent: 'space-between', 
        alignItems: 'center', 
        mb: 4,
        flexWrap: 'wrap',
        gap: 2
      }}>
        <Box>
          <Typography variant="h4" gutterBottom fontWeight="bold">
             Мои бронирования
          </Typography>
          <Typography color="textSecondary">
            Управление вашими бронированиями парковочных мест
          </Typography>
        </Box>
        
        <Button
          variant="contained"
          size="large"
          onClick={() => navigate('/slots')}
          startIcon={<Add />}
          sx={{ 
            bgcolor: '#1976d2',
            '&:hover': { bgcolor: '#1565c0' },
          }}
        >
          Создать бронирование
        </Button>
      </Box>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError('')}>
          {error}
        </Alert>
      )}

      {success && (
        <Alert severity="success" sx={{ mb: 2 }} onClose={() => setSuccess('')}>
          {success}
        </Alert>
      )}

      {reservations.length === 0 ? (
        <Paper sx={{ p: 4, textAlign: 'center' }}>
          <LocalParking sx={{ fontSize: 64, color: '#9e9e9e', mb: 2 }} />
          <Typography variant="h6" color="textSecondary" gutterBottom>
            У вас пока нет бронирований
          </Typography>
          <Typography color="textSecondary" sx={{ mb: 3 }}>
            Создайте первое бронирование прямо сейчас!
          </Typography>
          <Button
            variant="contained"
            size="large"
            onClick={() => navigate('/slots')}
            startIcon={<Add />}
          >
            Выбрать место
          </Button>
        </Paper>
      ) : (
        <Grid container spacing={3}>
          {reservations.map((res) => (
            <Grid item xs={12} key={res.id}>
              <Card 
                elevation={3}
                sx={{
                  borderLeft: res.status === 'active' ? '4px solid #4caf50' : 
                              res.status === 'pending' ? '4px solid #ff9800' : 
                              res.status === 'cancelled' ? '4px solid #f44336' :
                              '4px solid #9e9e9e',
                  transition: 'transform 0.2s',
                  '&:hover': {
                    transform: 'translateY(-2px)',
                    boxShadow: 6,
                  }
                }}
              >
                <CardContent>
                  <Grid container spacing={2}>
                    <Grid item xs={12} md={4}>
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 1 }}>
                        <Avatar sx={{ 
                          bgcolor: res.status === 'cancelled' ? '#f44336' : 'primary.main', 
                          width: 40, height: 40 
                        }}>
                          {res.booking_code?.charAt(0) || 'P'}
                        </Avatar>
                        <Box>
                          <Typography variant="h6" fontWeight="bold">
                            {res.booking_code}
                          </Typography>
                          <Typography variant="body2" color="textSecondary">
                            {res.zone_name || 'Zone'} • Место {res.slot_number}
                          </Typography>
                        </Box>
                      </Box>
                      
                      <Box sx={{ mt: 2 }}>
                        {getStatusChip(res.status)}
                      </Box>
                    </Grid>

                    <Grid item xs={12} md={3}>
                      <Box sx={{ display: 'flex', alignItems: 'flex-start', gap: 1, mb: 1 }}>
                        <Event sx={{ color: 'text.secondary', fontSize: 20 }} />
                        <Box>
                          <Typography variant="caption" color="textSecondary">
                            Начало
                          </Typography>
                          <Typography variant="body2">
                            {formatDate(res.start_time)}
                          </Typography>
                        </Box>
                      </Box>
                      
                      <Box sx={{ display: 'flex', alignItems: 'flex-start', gap: 1 }}>
                        <AccessTime sx={{ color: 'text.secondary', fontSize: 20 }} />
                        <Box>
                          <Typography variant="caption" color="textSecondary">
                            Окончание
                          </Typography>
                          <Typography variant="body2">
                            {formatDate(res.end_time)}
                          </Typography>
                        </Box>
                      </Box>
                    </Grid>

                    <Grid item xs={12} md={3}>
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                        <CarCrash sx={{ color: 'text.secondary' }} />
                        <Typography variant="body2" fontWeight="bold">
                          {res.license_plate || 'Не указан'}
                        </Typography>
                      </Box>
                      
                      {res.is_guest ? (
                        <Chip label="Гость" size="small" color="info" variant="outlined" />
                      ) : (
                        <Chip label="Зарегистрирован" size="small" color="success" variant="outlined" />
                      )}
                    </Grid>

                    <Grid item xs={12} md={2}>
                      <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
                        
                        <Tooltip title="Просмотр камеры (скоро)">
                          <Button
                            variant="outlined"
                            size="small"
                            onClick={() => navigate(`/camera/${res.slot}`)}
                            startIcon={<Videocam />}
                            disabled={res.status === 'cancelled'}
                            sx={{ justifyContent: 'flex-start', fontSize: '0.75rem', textTransform: 'none' }}
                          >
                             Камера
                          </Button>
                        </Tooltip>

                        {canConfirm(res.status) && (
                          <Tooltip title="Подтвердить прибытие">
                            <Button
                              variant="contained"
                              size="small"
                              onClick={() => handleConfirm(res.id)}
                              startIcon={<CheckCircle />}
                              sx={{ 
                                bgcolor: 'success.main',
                                '&:hover': { bgcolor: 'success.dark' },
                                justifyContent: 'flex-start',
                                fontSize: '0.75rem',
                                textTransform: 'none',
                              }}
                            >
                              Подтвердить
                            </Button>
                          </Tooltip>
                        )}

                        {canCancel(res.status) && (
                          <Tooltip title={res.status === 'active' ? 'Завершить бронь' : 'Отменить бронирование'}>
                            <Button
                              variant="outlined"
                              size="small"
                              onClick={() => handleCancel(res.id)}
                              startIcon={<Cancel />}
                              color="error"
                              sx={{ justifyContent: 'flex-start', fontSize: '0.75rem', textTransform: 'none' }}
                            >
                              {res.status === 'active' ? 'Завершить' : 'Отменить'}
                            </Button>
                          </Tooltip>
                        )}

                        <Tooltip title="Сообщить об угоне">
                          <Button
                            variant="outlined"
                            size="small"
                            onClick={() => navigate(`/theft-report/${res.id}`)}
                            startIcon={<Warning />}
                            color="error"
                            sx={{ justifyContent: 'flex-start', fontSize: '0.75rem', textTransform: 'none' }}
                          >
                             Угон
                          </Button>
                        </Tooltip>

                      </Box>
                    </Grid>
                  </Grid>
                </CardContent>
              </Card>
            </Grid>
          ))}
        </Grid>
      )}

      <Paper sx={{ mt: 4, p: 3, bgcolor: '#e3f2fd' }}>
        <Typography variant="subtitle2" gutterBottom fontWeight="bold">
           Информация:
        </Typography>
        <Typography variant="body2" color="textSecondary">
          • Максимальное время бронирования: 3 часа<br />
          • Максимум активных бронирований: 3<br />
          • Отмена возможна для статусов "Ожидает" и "Активно"<br />
          •  Функция видеонаблюдения в разработке
        </Typography>
      </Paper>

      <Fab
        color="primary"
        onClick={() => navigate('/slots')}
        sx={{
          position: 'fixed',
          bottom: 24,
          right: 24,
          display: { xs: 'flex', sm: 'none' },
        }}
      >
        <Add />
      </Fab>
    </Container>
  );
};

export default Dashboard;