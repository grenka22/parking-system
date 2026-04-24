import React, { useState, useEffect } from 'react';
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
} from '@mui/material';
import { zonesAPI, slotsAPI, reservationsAPI } from '../services/api';
import { useAuth } from '../context/AuthContext';

const Dashboard = () => {
  const { user } = useAuth();
  const [zones, setZones] = useState([]);
  const [availableSlots, setAvailableSlots] = useState([]);
  const [myReservations, setMyReservations] = useState([]);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      const [zonesRes, slotsRes, reservationsRes] = await Promise.all([
        zonesAPI.getAll(),
        slotsAPI.getAvailable(),
        reservationsAPI.getMyReservations(user?.email, ''),
      ]);

      setZones(zonesRes.data);
      setAvailableSlots(slotsRes.data.slice(0, 5));
      setMyReservations(reservationsRes.data);
    } catch (error) {
      console.error('Error fetching data:', error);
    }
  };

  return (
    <Container maxWidth="lg" sx={{ mt: 4, mb: 4 }}>
      <Typography variant="h4" gutterBottom>
        Добро пожаловать, {user?.username}!
      </Typography>

      <Grid container spacing={3}>
        {/* Статистика */}
        <Grid item xs={12} md={4}>
          <Card>
            <CardContent>
              <Typography color="textSecondary" gutterBottom>
                Всего зон
              </Typography>
              <Typography variant="h3">{zones.length}</Typography>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} md={4}>
          <Card>
            <CardContent>
              <Typography color="textSecondary" gutterBottom>
                Свободных мест
              </Typography>
              <Typography variant="h3">{availableSlots.length}</Typography>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} md={4}>
          <Card>
            <CardContent>
              <Typography color="textSecondary" gutterBottom>
                Мои брони
              </Typography>
              <Typography variant="h3">{myReservations.length}</Typography>
            </CardContent>
          </Card>
        </Grid>

        {/* Зоны парковки */}
        <Grid item xs={12}>
          <Paper sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>
              Зоны парковки
            </Typography>
            <Grid container spacing={2}>
              {zones.map((zone) => (
                <Grid item xs={12} md={4} key={zone.id}>
                  <Card>
                    <CardContent>
                      <Typography variant="h6">{zone.name}</Typography>
                      <Typography color="textSecondary">
                        Тип: {zone.zone_type}
                      </Typography>
                      <Typography color="textSecondary">
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
          </Paper>
        </Grid>

        {/* Доступные места */}
        <Grid item xs={12}>
          <Paper sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>
              Свободные места
            </Typography>
            {availableSlots.length > 0 ? (
              <Grid container spacing={2}>
                {availableSlots.map((slot) => (
                  <Grid item xs={12} md={3} key={slot.id}>
                    <Card>
                      <CardContent>
                        <Typography variant="h6">Место {slot.number}</Typography>
                        <Typography color="textSecondary">
                          Зона: {slot.zone_name}
                        </Typography>
                        <Button
                          variant="contained"
                          size="small"
                          sx={{ mt: 1 }}
                          onClick={() => (window.location.href = `/book/${slot.id}`)}
                        >
                          Забронировать
                        </Button>
                      </CardContent>
                    </Card>
                  </Grid>
                ))}
              </Grid>
            ) : (
              <Typography color="textSecondary">
                Нет доступных мест
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
              myReservations.map((reservation) => (
                <Card key={reservation.id} sx={{ mb: 2 }}>
                  <CardContent>
                    <Grid container spacing={2}>
                      <Grid item xs={12} md={3}>
                        <Typography variant="subtitle1">
                          Код: {reservation.booking_code}
                        </Typography>
                      </Grid>
                      <Grid item xs={12} md={3}>
                        <Typography>
                          Место: {reservation.slot_number}
                        </Typography>
                      </Grid>
                      <Grid item xs={12} md={3}>
                        <Typography>
                          {new Date(reservation.start_time).toLocaleString()}
                        </Typography>
                      </Grid>
                      <Grid item xs={12} md={3}>
                        <Chip
                          label={reservation.status}
                          color={
                            reservation.status === 'active' ? 'success' : 'default'
                          }
                          size="small"
                        />
                      </Grid>
                    </Grid>
                  </CardContent>
                </Card>
              ))
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