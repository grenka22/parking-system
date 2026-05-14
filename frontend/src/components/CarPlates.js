import React, { useState } from 'react';
import { TextField, Typography, Box, FormControl, FormControlLabel, RadioGroup, Radio, FormHelperText } from '@mui/material';

const CarPlates = ({ value, onChange, error, helperText, required = true }) => {
  const [plate, setPlate] = useState(value || '');
  const [country, setCountry] = useState('ru');

  // Форматирование русского номера: Х000ХХ 00
  const formatRU = (input) => {
    let c = input.toUpperCase().replace(/[^АВЕКМНОРСТУХ0-9]/gi, '');
    if (c.length > 9) c = c.slice(0, 9);
    let r = '';
    if (c[0]) r += c[0];
    if (c.slice(1,4)) r += c.slice(1,4);
    if (c.slice(4,6)) r += c.slice(4,6);
    if (c.slice(6,8)) r += ' ' + c.slice(6,8);
    return r;
  };

  // Форматирование белорусского номера: 0000 ХХ-0
  const formatBY = (input) => {
    let c = input.toUpperCase().replace(/[^ABEHKMOPTX0-9]/gi, '');
    if (c.length > 7) c = c.slice(0, 7);
    let r = '';
    if (c.slice(0,4)) r += c.slice(0,4);
    if (c.slice(4,6)) r += ' ' + c.slice(4,6);
    if (c.slice(6,7)) r += '-' + c.slice(6,7);
    return r;
  };

  const handleChange = (e) => {
    const raw = e.target.value;
    const formatted = country === 'ru' ? formatRU(raw) : formatBY(raw);
    setPlate(formatted);
    if (onChange) onChange(formatted);
  };

  const handleCountry = (e) => {
    setCountry(e.target.value);
    setPlate('');
    if (onChange) onChange('');
  };

  const clean = plate.replace(/[\s-]/g, '');
  const hasError = error || (required && plate && clean.length < 6);

  return (
    <Box sx={{ mt: 2, mb: 2 }}>
      {/* Выбор страны */}
      <FormControl component="fieldset" sx={{ mb: 2 }}>
        <Typography variant="subtitle2" fontWeight="bold" gutterBottom>
          Страна автомобиля
        </Typography>
        <RadioGroup row value={country} onChange={handleCountry}>
          <FormControlLabel value="ru" control={<Radio size="small" />} label="🇷🇺 РФ" />
          <FormControlLabel value="by" control={<Radio size="small" />} label="🇧🇾 РБ" />
        </RadioGroup>
      </FormControl>

      {/* Поле ввода */}
      <Typography variant="subtitle2" fontWeight="bold" gutterBottom>
        Номер {required && <span style={{color:'red'}}>*</span>}
      </Typography>
      
      <Box sx={{
        border: country === 'ru' ? '3px solid #000' : '2px solid #0066cc',
        borderRadius: 1, bgcolor: '#fff', p: 1, maxWidth: 320,
        display: 'flex', alignItems: 'center', gap: 1,
        ...(hasError ? { borderColor: '#d32f2f' } : {})
      }}>
        {/* Флаг */}
        <Box sx={{
          width: 20, height: 32, borderRadius: 0.5,
          background: country === 'ru' 
            ? 'linear-gradient(#fff 33%,#0039A6 33%,#0039A6 66%,#D52B1E 66%)'
            : 'linear-gradient(#009739 33%,#fff 33%,#fff 66%,#CE1126 66%)'
        }} />
        
        <TextField
          value={plate}
          onChange={handleChange}
          placeholder={country === 'ru' ? 'Х000ХХ 00' : '0000 ХХ-0'}
          variant="standard"
          fullWidth
          InputProps={{
            disableUnderline: true,
            sx: {
              fontSize: 20, fontWeight: 'bold', fontFamily: 'monospace',
              letterSpacing: 1, color: '#000',
              '&::placeholder': { color: '#999', opacity: 0.6 }
            }
          }}
        />
      </Box>

      {helperText && <FormHelperText>{helperText}</FormHelperText>}
      {hasError && (
        <FormHelperText error>
          {country === 'ru' ? 'Пример: А123БВ 77' : 'Пример: 1234 AB-7'}
        </FormHelperText>
      )}
      <Typography variant="caption" color="textSecondary" sx={{display:'block', mt: 0.5}}>
        {country === 'ru' ? 'Буквы: А,В,Е,К,М,Н,О,Р,С,Т,У,Х' : 'Буквы: A,B,E,H,K,M,O,P,T,X'}
      </Typography>
    </Box>
  );
};

export default CarPlates;