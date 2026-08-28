import { useEffect, useRef, useState } from 'react';
import type { Conversation, Message } from '../types';
import type { AssistantService } from '../services/openclaw';

const STORAGE_KEY = 'orion-conversations';

const seedConversations: Conversation[] = [
  {
    id: 'welcome', title: 'Primeros pasos con Orion', preview: '¿Qué puedes hacer?', updatedAt: 'Ahora',
    messages: [{ id: 'welcome-message', role: 'assistant', content: 'Hola. Soy Orion, tu espacio de trabajo inteligente. ¿Qué te gustaría explorar?', createdAt: new Date().toISOString() }],
  },
  { id: 'planning', title: 'Planificación trimestral', preview: 'Notas de la reunión...', updatedAt: 'Ayer', messages: [] },
  { id: 'research', title: 'Investigación de mercado', preview: 'Comparativa de alternativas', updatedAt: 'Lun', messages: [] },
];

const createId = () => `${Date.now()}-${Math.random().toString(36).slice(2)}`;

function loadConversations(): Conversation[] {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    return stored ? (JSON.parse(stored) as Conversation[]) : seedConversations;
  } catch {
    return seedConversations;
  }
}

export function useChat(service: AssistantService) {
  const [conversations, setConversations] = useState<Conversation[]>(loadConversations);
  const [activeId, setActiveId] = useState('welcome');
  const [isGenerating, setIsGenerating] = useState(false);
  const activeConversation = conversations.find((conversation) => conversation.id === activeId) ?? conversations[0];

  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(conversations));
  }, [conversations]);

  const selectConversation = (id: string) => {
    if (!isGenerating) setActiveId(id);
  };

  const createConversation = () => {
    if (isGenerating) return;
    const conversation: Conversation = { id: createId(), title: 'Nueva conversación', preview: 'Comienza una nueva idea', updatedAt: 'Ahora', messages: [] };
    setConversations((current) => [conversation, ...current]);
    setActiveId(conversation.id);
  };

  const sendMessage = async (content: string) => {
    console.log('[useChat] sendMessage recibido', { contentLength: content.trim().length, isGenerating, activeConversationId: activeConversation?.id });
    if (!content.trim() || isGenerating || !activeConversation) {
      console.warn('[useChat] envío detenido por validación');
      return;
    }
    const userMessage: Message = { id: createId(), role: 'user', content: content.trim(), createdAt: new Date().toISOString() };
    const nextMessages = [...activeConversation.messages, userMessage];
    console.log('[useChat] mensaje preparado', { messageCount: nextMessages.length });
    setConversations((current) => current.map((conversation) => conversation.id === activeId ? { ...conversation, title: conversation.messages.length ? conversation.title : content.trim().slice(0, 28), preview: content.trim(), updatedAt: 'Ahora', messages: nextMessages } : conversation));
    setIsGenerating(true);
    console.log('[useChat] llamando a service.sendMessage');
    try {
      const response = await service.sendMessage(nextMessages);
      console.log('[useChat] respuesta recibida del servicio', { responseLength: response.length });
      const assistantMessage: Message = { id: createId(), role: 'assistant', content: response, createdAt: new Date().toISOString() };
      setConversations((current) => current.map((conversation) => conversation.id === activeId ? { ...conversation, preview: response, updatedAt: 'Ahora', messages: [...nextMessages, assistantMessage] } : conversation));
    } catch (error) {
      console.error('[useChat] error al llamar al servicio', error);
      const message = error instanceof Error ? error.message : 'No se pudo obtener una respuesta del asistente. Intentá nuevamente.';
      const errorMessage: Message = { id: createId(), role: 'assistant', content: message, createdAt: new Date().toISOString() };
      setConversations((current) => current.map((conversation) => conversation.id === activeId ? { ...conversation, preview: message, updatedAt: 'Ahora', messages: [...nextMessages, errorMessage] } : conversation));
    } finally {
      setIsGenerating(false);
      console.log('[useChat] proceso de envío finalizado');
    }
  };

  return { conversations, activeConversation, isGenerating, selectConversation, createConversation, sendMessage };
}
