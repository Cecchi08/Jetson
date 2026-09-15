import { callN8n } from '../services/n8nService.js';

const VALID_MODES = ['chat', 'web', 'pdf', 'ask'];

export async function chat(req, res) {
  try {
    const { message, mode = 'chat' } = req.body ?? {};

    if (typeof message !== 'string' || !message.trim()) {
      return res.status(400).json({
        error: 'El campo message es obligatorio',
      });
    }

    if (!VALID_MODES.includes(mode)) {
      return res.status(400).json({
        error: 'Modo inválido. Valores permitidos: chat, web, pdf, ask',
      });
    }

    const response = await callN8n({
      message: message.trim(),
      mode,
    });

    return res.status(200).json({ response });
  } catch (error) {
    console.error('Error en /api/chat:', error.message);

    if (error?.name === 'TimeoutError') {
      return res.status(504).json({
        error: 'n8n tardó demasiado en responder',
      });
    }

    if (
      error?.message?.includes('ECONNREFUSED') ||
      error?.message?.includes('fetch failed')
    ) {
      return res.status(503).json({
        error: 'n8n no está disponible',
      });
    }

    return res.status(500).json({
      error: 'No se pudo procesar la solicitud',
    });
  }
}
