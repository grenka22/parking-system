import React, { useState } from 'react';
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
  Stepper,
  Step,
  StepLabel,
  Card,
  CardContent,
} from '@mui/material';
import { theftAPI } from '../services/api';

const TheftReport = () => {
  const { reservationId } = useParams();
  const navigate = useNavigate();
  const [step, setStep] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  
  const [formData, setFormData] = useState({
    reservation: reservationId || null,
    user_name: '',
    user_phone: '',
    description: '',
  });

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      if (!formData.description || formData.description.length < 10) {
        throw new Error('Опишите ситуацию подробнее (минимум 10 символов)');
      }
      if (!formData.user_name || !formData.user_phone) {
        throw new Error('Заполните имя и телефон');
      }
      await theftAPI.create(formData);
      setSuccess('✅ Заявление успешно отправлено!');
      setStep(2);
    } catch (err) {
      setError(err.response?.data?.error || err.message || 'Ошибка при отправке');
    } finally {
      setLoading(false);
    }
  };

  const steps = ['Информация', 'Заполнение', 'Отправка'];

  return (
    <Container maxWidth="md" sx={{ mt: 8, mb: 4 }}>
      <Paper elevation={3} sx={{ p: 4 }}>
        <Typography variant="h4" gutterBottom align="center" color="error">
          🚨 Заявление об угоне
        </Typography>

        <Stepper activeStep={step} sx={{ mt: 3, mb: 4 }}>
          {steps.map((label) => (
            <Step key={label}><StepLabel>{label}</StepLabel></Step>
          ))}
        </Stepper>

        {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}
        {success && <Alert severity="success" sx={{ mb: 2 }}>{success}</Alert>}

        {step === 0 && (
          <Card sx={{ mb: 3 }}>
            <CardContent>
              <Typography variant="h6" gutterBottom>📋 Важная информация</Typography>
              <Typography variant="body1" paragraph>
                Если ваш автомобиль был угнан с парковки, заполните заявление.
              </Typography>
              <Alert severity="warning" sx={{ mt: 2 }}>
                ⚠️ Ложное заявление — уголовное преступление!
              </Alert>
              <Box sx={{ mt: 3, display: 'flex', gap: 2 }}>
                <Button variant="contained" color="error" size="large" 
                  onClick={() => setStep(1)} fullWidth>ПРОДОЛЖИТЬ</Button>
                <Button variant="outlined" size="large" 
                  onClick={() => navigate('/dashboard')}>ОТМЕНА</Button>
              </Box>
            </CardContent>
          </Card>
        )}

        {step === 1 && (
          <Box component="form" onSubmit={handleSubmit}>
            <TextField fullWidth label="Ваше имя *" name="user_name"
              value={formData.user_name} onChange={handleChange} margin="normal" required />
            <TextField fullWidth label="Телефон *" name="user_phone"
              value={formData.user_phone} onChange={handleChange} margin="normal" required />
            <TextField fullWidth multiline rows={6} label="Описание *" name="description"
              value={formData.description} onChange={handleChange} margin="normal" required
              helperText={`${formData.description.length}/10 мин.`} />
            <Box sx={{ display: 'flex', gap: 2, mt: 3 }}>
              <Button type="submit" variant="contained" color="error" size="large" 
                fullWidth disabled={loading}>
                {loading ? <CircularProgress size={24} /> : '🚨 ОТПРАВИТЬ'}
              </Button>
              <Button variant="outlined" size="large" onClick={() => setStep(0)}>НАЗАД</Button>
            </Box>
          </Box>
        )}

        {step === 2 && (
          <Box sx={{ textAlign: 'center', py: 4 }}>
            <Typography variant="h5" color="success.main">✅ Отправлено!</Typography>
            <Button variant="contained" onClick={() => navigate('/dashboard')} sx={{ mt: 3 }}>
              НА ГЛАВНУЮ
            </Button>
          </Box>
        )}
      </Paper>
    </Container>
  );
};

export default TheftReport;