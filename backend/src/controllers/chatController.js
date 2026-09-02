import { callOrchestrator } from '../services/orchestratorService.js';

// Puerto donde el orquestador sirve los PDFs generados (servidor HTTP de PDFs).
const PDF_PORT = process.env.PDF_PORT || '9081';

// Reescribe las URLs de PDFs para usar el host desde el que navega el usuario,
// manteniendo el puerto del servidor de PDFs (p. ej. http://172.15.0.202:9081/pdfs/...).
function reescribirEnlacesPdf(texto, host) {
  const hostname = host ? host.split(':')[0] : 'localhost';
  return texto.replace(/https?:\/\/[^\s/]+\/pdfs\//g, `http://${hostname}:${PDF_PORT}/pdfs/`);
}

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

    // Los enlaces a PDFs deben apuntar al mismo host/puerto desde el que navega el usuario
    const host = req.get('host') || 'localhost';
    const responseFinal = reescribirEnlacesPdf(response, host);

    return res.status(200).json({ response: responseFinal });
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
