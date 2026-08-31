import { sendToOpenClaw } from '../services/openclawService.js';
import { persistChatConversation } from '../services/conversationService.js';

export async function chat(req, res) {
  try {
    const { messages } = req.body;

    if (!Array.isArray(messages) || messages.length === 0) {
      return res.status(400).json({ error: 'messages debe ser un array no vacío' });
    }

    if (!messages.every((msg) => msg.role && msg.content && typeof msg.content === 'string')) {
      return res.status(400).json({ error: 'Cada mensaje debe tener role y content' });
    }

    const response = await sendToOpenClaw(messages);

    try {
      await persistChatConversation(messages, response);
      console.log('Conversación persistida en PostgreSQL');
    } catch (dbError) {
      console.error('No se pudo guardar la conversación:', dbError.message);
    }

    res.json({
      message: {
        role: 'assistant',
        content: response,
      },
    });
  } catch (error) {
    console.error('Error en /api/chat:', error.message);

    if (error.message.includes('OPENCLAW')) {
      return res.status(503).json({ error: 'El asistente no está disponible' });
    }

    res.status(500).json({ error: 'No se pudo procesar la solicitud' });
  }
}
