import type { Message } from '../types';

export interface AssistantService {
  respond(messages: Message[]): Promise<string>;
}

const cannedResponses: Record<string, string> = {
  hola: 'Hola. Soy Orion, tu espacio de trabajo inteligente. ¿Qué te gustaría explorar?',
  gracias: 'De nada. Cuando quieras, seguimos.',
  ayuda: 'Puedo ayudarte a ordenar ideas, redactar documentos o convertir preguntas complejas en próximos pasos claros.',
};

const fallback = 'He recibido tu mensaje. Esta interfaz está lista para conectarse a un asistente empresarial cuando incorporemos el backend.';

export const localAssistantService: AssistantService = {
  respond: async (messages) => {
    await new Promise((resolve) => window.setTimeout(resolve, 850));
    const latest = messages[messages.length - 1]?.content.trim().toLowerCase() ?? '';
    return cannedResponses[latest] ?? fallback;
  },
};
