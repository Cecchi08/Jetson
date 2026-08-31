import express from 'express';
import chatRoutes from './routes/chat.js';

const app = express();

app.use(express.json());

app.use('/api', chatRoutes);

app.get('/health', (req, res) => {
  res.json({ status: 'ok' });
});

app.use((err, req, res, next) => {
  console.error(err.stack);
  res.status(500).json({ error: 'Algo salió mal. Intentá más tarde.' });
});

export default app;
