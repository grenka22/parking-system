import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Container,
  Box,
  Typography,
  Grid,
  Card,
  CardContent,
  Button,
  Chip,
  CircularProgress,
  Alert,
} from '@mui/material';
import { LocationOn, CheckCircle } from '@mui/icons-material';
import { slotsAPI } from '../services/api';

const Slots = () => {
  const navigate = useNavigate();
  const [slots, setSlots] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    fetchSlots();
  }, []);

  const fetchSlots = async () => {
    try {
      setLoading(true);
      const response = await slotsAPI.getAll();
      setSlots(response.data);
    } catch (err) {
      setError('Не удалось загрузить места');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <Container maxWidth="lg" sx={{ mt: 8, textAlign: 'center' }}>
        <CircularProgress />
        <Typography sx={{ mt: 2 }}>Загрузка мест...</Typography>
      </Container>
    );
  }

  return (
    <Container maxWidth="lg" sx={{ mt: 8, mb: 4 }}>
      <Typography variant="h4" gutterBottom fontWeight="bold">
         Выбор парковочного места
      </Typography>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}

      <Grid container spacing={3}>
        {slots.map((slot) => (
          <Grid item xs={12} sm={6} md={4} key={slot.id}>
            <Card 
              elevation={3}
              sx={{
                borderLeft: slot.is_active ? '4px solid #4caf50' : '4px solid #f44336',
                transition: 'transform 0.2s',
                '&:hover': {
                  transform: 'translateY(-4px)',
                  boxShadow: 6,
                }
              }}
            >
              <CardContent>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                  <Typography variant="h6" fontWeight="bold">
                    Место {slot.number}
                  </Typography>
                  <Chip
                    icon={slot.is_active ? <CheckCircle /> : null}
                    label={slot.is_active ? 'Активно' : 'Неактивно'}
                    color={slot.is_active ? 'success' : 'default'}
                    size="small"
                  />
                </Box>

                <Typography variant="body2" color="textSecondary" gutterBottom>
                  <LocationOn sx={{ fontSize: 16, verticalAlign: 'middle', mr: 0.5 }} />
                  Зона: {slot.zone?.name || 'N/A'}
                </Typography>

                {slot.zone_type && (
                  <Chip label={slot.zone_type} size="small" sx={{ mt: 1, mr: 1 }} />
                )}

                <Button
                  variant="contained"
                  fullWidth
                  sx={{ mt: 2 }}
                  onClick={() => navigate(`/book/${slot.id}`)}
                  disabled={!slot.is_active}
                >
                  {slot.is_active ? 'ЗАБРОНИРОВАТЬ' : 'НЕДОСТУПНО'}
                </Button>
              </CardContent>
            </Card>
          </Grid>
        ))}
      </Grid>
    </Container>
  );
};

export default Slots;