import express from 'express';
import chatRoutes from './routes/chat.js';
import authRoutes from './routes/auth.js';
import { verifyToken } from './middleware/auth.js';

const app = express();

app.use(express.json());

// Rutas públicas
app.use('/api/auth', authRoutes);

// Rutas protegidas
app.use('/api/chat', verifyToken);
app.use('/api', chatRoutes);

app.get('/health', (req, res) => {
  res.json({ status: 'ok' });
});

app.use((err, req, res, next) => {
  console.error(err.stack);
  res.status(500).json({ error: 'Algo salió mal. Intentá más tarde.' });
});

export default app;
