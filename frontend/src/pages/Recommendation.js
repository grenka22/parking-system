import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Container,
  Box,
  Typography,
  TextField,
  Button,
  Paper,
  Card,
  CardContent,
  Grid,
  Chip,
  Alert,
  CircularProgress,
  Rating,
} from '@mui/material';
import { slotsAPI } from '../services/api';

const Recommendation = () => {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [recommendations, setRecommendations] = useState([]);
  const [error, setError] = useState('');
  
  const [formData, setFormData] = useState({
    start_time: '',
    end_time: '',
    zone_type: '',
  });

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
  };

  const handleRecommend = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      const response = await slotsAPI.recommend(formData);
      setRecommendations(response.data.recommendations || []);
      
      if (!response.data.success) {
        setError(response.data.message || 'Нет доступных мест');
      }
    } catch (err) {
      setError(err.response?.data?.error || 'Ошибка при получении рекомендаций');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Container maxWidth="md" sx={{ mt: 8, mb: 4 }}>
      <Typography variant="h4" gutterBottom>
         Умный подбор места
      </Typography>

      <Paper sx={{ p: 3, mb: 3 }}>
        <Box component="form" onSubmit={handleRecommend}>
          <Grid container spacing={2}>
            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                label="Время начала *"
                sx={{
                  '& .MuiInputBase-input': {
                    padding: '12px 14px',
                    fontSize: '14px',
                  },
                  minWidth: 200,  
                  }}       
                type="datetime-local"
                name="start_time"
                value={formData.start_time}
                onChange={handleChange}
                InputLabelProps={{ shrink: true }}
                required
              />
            </Grid>
            
            <Grid item xs={12} sm={6}>
              <TextField
                fullWidth
                label="Время окончания *"
                type="datetime-local"
                name="end_time"
                value={formData.end_time}
                onChange={handleChange}
                InputLabelProps={{ shrink: true }}
                required
              />
            </Grid>

            <Grid item xs={12}>
              <TextField
                fullWidth
                select
                label="Тип зоны (необязательно)"
                name="zone_type"
                value={formData.zone_type}
                onChange={handleChange}
                SelectProps={{ native: true }}
              >
                <option value="">Любой тип</option>
                <option value="entrance">У входа</option>
                <option value="regular">Обычная</option>
                <option value="vip">VIP</option>
              </TextField>
            </Grid>

            <Grid item xs={12}>
              <Button
                type="submit"
                variant="contained"
                size="large"
                fullWidth
                disabled={loading}
              >
                {loading ? <CircularProgress size={24} /> : '🔍 НАЙТИ ЛУЧШЕЕ МЕСТО'}
              </Button>
            </Grid>
          </Grid>
        </Box>
      </Paper>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}

      {recommendations.length > 0 && (
        <Box>
          <Typography variant="h6" gutterBottom>
            Рекомендуемые места:
          </Typography>
          
          {recommendations.map((rec) => (
            <Card key={rec.rank} sx={{ mb: 2, borderLeft: rec.rank === 1 ? '4px solid #4caf50' : '4px solid #2196f3' }}>
              <CardContent>
                <Grid container spacing={2} alignItems="center">
                  <Grid item xs={12} sm={3}>
                    <Typography variant="h6">
                      {rec.rank === 1 }
                      {rec.rank === 2 }
                      {rec.rank === 3 }
                      Место {rec.slot_number}
                    </Typography>
                    <Typography color="textSecondary">
                      {rec.zone_name}
                    </Typography>
                  </Grid>
                  
                  <Grid item xs={12} sm={3}>
                    <Chip
                      label={rec.zone_type || 'Обычная'}
                      color={rec.rank === 1 ? 'success' : 'primary'}
                      size="small"
                    />
                  </Grid>
                  
                  <Grid item xs={12} sm={3}>
                    <Typography variant="body2">
                      Загруженность: {rec.zone_load_percent}%
                    </Typography>
                    <Typography variant="caption" color="textSecondary">
                      Score: {rec.score}
                    </Typography>
                  </Grid>
                  
                  <Grid item xs={12} sm={3}>
                    <Typography variant="body2" color="textSecondary">
                      {rec.reason}
                    </Typography>
                    <Button
                      size="small"
                      variant="contained"
                      onClick={() => navigate(`/book/${rec.slot_id}`)}
                      sx={{ mt: 1 }}
                    >
                      ЗАБРОНИРОВАТЬ
                    </Button>
                  </Grid>
                </Grid>
              </CardContent>
            </Card>
          ))}
        </Box>
      )}
    </Container>
  );
};

export default Recommendation;