import { callOrchestrator } from '../services/orchestratorService.js';

export async function chat(req, res) {
  try {
    const { message, history = [] } = req.body ?? {};

    if (typeof message !== 'string' || !message.trim()) {
      return res.status(400).json({ error: 'El campo message es obligatorio' });
    }

    if (!Array.isArray(history)) {
      return res.status(400).json({ error: 'El campo history debe ser un array' });
    }

    const response = await callOrchestrator({
      message: message.trim(),
      history: history.map((item) => ({
        role: item?.role ?? 'user',
        content: String(item?.content ?? ''),
      })).filter((item) => item.content.trim()),
    });

    return res.status(200).json({ response });
  } catch (error) {
    console.error('Error en /api/chat:', error.message);

    if (error?.name === 'TimeoutError') {
      return res.status(504).json({ error: 'El orquestador tardó demasiado en responder' });
    }

    if (error?.message?.includes('ECONNREFUSED') || error?.message?.includes('fetch failed')) {
      return res.status(503).json({ error: 'El orquestador no está disponible' });
    }

    return res.status(500).json({ error: 'No se pudo procesar la solicitud' });
  }
}
