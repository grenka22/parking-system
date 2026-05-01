import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';
import Login from './pages/Login';
import Register from './pages/Register';
import Dashboard from './pages/Dashboard';
import Booking from './pages/Booking';
import { Container, Button, AppBar, Toolbar, Typography, Box } from '@mui/material';

const NavBar = () => {
  const { user, logout } = useAuth();

  return (
    <AppBar position="static">
      <Toolbar>
        <Typography variant="h6" sx={{ flexGrow: 1 }}>
          Система парковки
        </Typography>
        {user ? (
          <>
            <Typography sx={{ mr: 2 }}>👤 {user.username}</Typography>
            <Button color="inherit" onClick={() => (window.location.href = '/dashboard')}>
              Главная
            </Button>
            <Button color="inherit" onClick={logout}>
              Выйти
            </Button>
          </>
        ) : (
          <>
            <Button color="inherit" onClick={() => (window.location.href = '/login')}>
              Войти
            </Button>
            <Button color="inherit" onClick={() => (window.location.href = '/register')}>
              Регистрация
            </Button>
          </>
        )}
      </Toolbar>
    </AppBar>
  );
};

const PrivateRoute = ({ children }) => {
  const { user, loading } = useAuth();

  if (loading) return <div>Загрузка...</div>;
  return user ? children : <Navigate to="/login" />;
};

function App() {
  return (
    <AuthProvider>
      <Router>  {/* ← Router должен быть ЗДЕСЬ! */}
        <NavBar />
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />
          <Route
            path="/dashboard"
            element={
              <PrivateRoute>
                <Dashboard />
              </PrivateRoute>
            }
          />
          <Route
            path="/book/:slotId"
            element={
              <PrivateRoute>
                <Booking />
              </PrivateRoute>
            }
          />
          <Route path="/" element={<Navigate to="/dashboard" />} />
        </Routes>
      </Router>
    </AuthProvider>
  );
}

export default App;