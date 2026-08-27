import { useEffect, useRef, useState } from 'react';
import type { Conversation, Message } from '../types';
import type { AssistantService } from '../services/assistantService';

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
  const [streamingMessage, setStreamingMessage] = useState<Message | null>(null);
  const streamTimer = useRef<number | undefined>(undefined);
  const activeConversation = conversations.find((conversation) => conversation.id === activeId) ?? conversations[0];

  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(conversations));
  }, [conversations]);

  useEffect(() => () => window.clearInterval(streamTimer.current), []);

  const selectConversation = (id: string) => {
    if (!isGenerating) { setActiveId(id); setStreamingMessage(null); }
  };

  const createConversation = () => {
    if (isGenerating) return;
    const conversation: Conversation = { id: createId(), title: 'Nueva conversación', preview: 'Comienza una nueva idea', updatedAt: 'Ahora', messages: [] };
    setConversations((current) => [conversation, ...current]);
    setActiveId(conversation.id);
  };

  const sendMessage = async (content: string) => {
    if (!content.trim() || isGenerating || !activeConversation) return;
    const userMessage: Message = { id: createId(), role: 'user', content: content.trim(), createdAt: new Date().toISOString() };
    const nextMessages = [...activeConversation.messages, userMessage];
    setConversations((current) => current.map((conversation) => conversation.id === activeId ? { ...conversation, title: conversation.messages.length ? conversation.title : content.trim().slice(0, 28), preview: content.trim(), updatedAt: 'Ahora', messages: nextMessages } : conversation));
    setIsGenerating(true);
    const response = await service.respond(nextMessages);
    const assistantMessage: Message = { id: createId(), role: 'assistant', content: '', createdAt: new Date().toISOString() };
    setStreamingMessage(assistantMessage);
    let index = 0;
    streamTimer.current = window.setInterval(() => {
      index += 1;
      const contentSoFar = response.slice(0, index);
      setStreamingMessage({ ...assistantMessage, content: contentSoFar });
      if (index >= response.length) {
        window.clearInterval(streamTimer.current);
        setConversations((current) => current.map((conversation) => conversation.id === activeId ? { ...conversation, preview: response, updatedAt: 'Ahora', messages: [...nextMessages, { ...assistantMessage, content: response }] } : conversation));
        setStreamingMessage(null);
        setIsGenerating(false);
      }
    }, 22);
  };

  return { conversations, activeConversation, isGenerating, streamingMessage, selectConversation, createConversation, sendMessage };
}
