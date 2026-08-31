import { Bot, Copy, RotateCcw, UserRound } from 'lucide-react';
import { useEffect, useRef } from 'react';
import type { Message } from '../types';

interface MessageListProps { messages: Message[]; streamingMessage: Message | null; isGenerating: boolean; }

export function MessageList({ messages, streamingMessage, isGenerating }: MessageListProps) {
  const bottomRef = useRef<HTMLDivElement>(null);
  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: 'smooth' }); }, [messages, streamingMessage]);
  return <div className="messages" aria-live="polite">{messages.map((message) => <MessageBubble key={message.id} message={message} />)}{isGenerating && !streamingMessage && <div className="typing"><span className="message-avatar message-avatar--assistant"><Bot size={16} /></span><div className="typing__dots"><i /><i /><i /></div><span>Orion está pensando</span></div>}<div ref={bottomRef} /></div>;
}

function MessageBubble({ message }: { message: Message }) {
  const isUser = message.role === 'user';
  return <article className={`message-row ${isUser ? 'message-row--user' : ''}`}><div className={`message-avatar ${isUser ? 'message-avatar--user' : 'message-avatar--assistant'}`}>{isUser ? <UserRound size={16} /> : <Bot size={16} />}</div><div className="message-content"><div className="message-meta"><strong>{isUser ? 'Tú' : 'Orion'}</strong><time>{isUser ? 'Ahora' : 'Asistente'}</time></div><p className="message-text">{message.content}</p>{!isUser && <div className="message-actions"><button aria-label="Copiar mensaje"><Copy size={13} /></button><button aria-label="Regenerar respuesta"><RotateCcw size={13} /></button></div>}</div></article>;
}
