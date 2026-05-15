import React from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Container,
  Box,
  Typography,
  Paper,
  Button,
  Chip,
  Grid,
  Card,
  CardContent,
} from '@mui/material';
import { VideocamOff, Construction, Star, AutoAwesome } from '@mui/icons-material';

const CameraStub = () => {
  const { slotId } = useParams();
  const navigate = useNavigate();

  return (
    <Container maxWidth="md" sx={{ mt: 8, mb: 4 }}>
      <Paper elevation={3} sx={{ p: 4, textAlign: 'center' }}>
        {/* Иконка */}
        <Box sx={{ 
          width: 120, height: 120, borderRadius: '50%', 
          bgcolor: '#f5f5f5', display: 'flex', 
          alignItems: 'center', justifyContent: 'center', 
          margin: '0 auto 24px' 
        }}>
          <VideocamOff sx={{ fontSize: 60, color: '#9e9e9e' }} />
        </Box>
        
        {/* Заголовок */}
        <Typography variant="h4" gutterBottom fontWeight="bold">
           Камера в разработке
        </Typography>
        
        <Typography variant="h6" color="textSecondary" paragraph>
          Функция просмотра камеры будет доступна скоро!
        </Typography>
        
        {/* Badge Coming Soon */}
        <Box sx={{ my: 3 }}>
          <Chip
            label="Coming Soon"
            color="warning"
            size="large"
            icon={<Construction />}
            sx={{ fontWeight: 'bold' }}
          />
        </Box>
        
        {/* Что будет доступно */}
        <Typography variant="body1" color="textSecondary" sx={{ mb: 3 }}>
          Мы работаем над интеграцией системы видеонаблюдения с распознаванием номеров.
          После подключения вы сможете:
        </Typography>
        
        <Grid container spacing={2} sx={{ mb: 4, textAlign: 'left' }}>
          {[
            { icon: '📹', text: 'Просматривать видео с камеры вашего места' },
            { icon: '🔍', text: 'Автоматическое распознавание номера' },
            { icon: '✅', text: 'Авто-подтверждение прибытия' },
            { icon: '📁', text: 'Доступ к записям с парковки' },
          ].map((item, idx) => (
            <Grid item xs={12} sm={6} key={idx}>
              <Card variant="outlined">
                <CardContent sx={{ py: 1, display: 'flex', alignItems: 'center', gap: 1 }}>
                  <Typography fontSize={20}>{item.icon}</Typography>
                  <Typography variant="body2">{item.text}</Typography>
                </CardContent>
              </Card>
            </Grid>
          ))}
        </Grid>
        
        {/* Как это работает (для интереса) */}
        <Paper sx={{ p: 2, bgcolor: '#e3f2fd', mb: 3 }}>
          <Typography variant="subtitle2" fontWeight="bold" gutterBottom>
            <AutoAwesome sx={{ verticalAlign: 'middle', mr: 0.5 }} />
            Как будет работать система:
          </Typography>
          <Typography variant="body2" color="textSecondary">
            1. Вы бронируете место → 2. Приезжаете на парковку → 
            3. Камера распознаёт номер → 4. Бронь подтверждается автоматически!
          </Typography>
        </Paper>
        
        {/* Кнопки навигации */}
        <Box sx={{ display: 'flex', gap: 2, justifyContent: 'center', flexWrap: 'wrap' }}>
          <Button
            variant="contained"
            size="large"
            onClick={() => navigate('/dashboard')}
            startIcon={<Star />}
          >
            На дашборд
          </Button>
          
          <Button
            variant="outlined"
            size="large"
            onClick={() => navigate(`/book/${slotId}`)}
          >
            К бронированию
          </Button>
        </Box>
        
        {/* Футер */}
        <Typography variant="caption" color="textSecondary" sx={{ mt: 4, display: 'block' }}>
          ID места: {slotId} • Версия: 1.0 • Статус: 🚧 В разработке
        </Typography>
      </Paper>
    </Container>
  );
};

export default CameraStub;