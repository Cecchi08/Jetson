import { Menu, MoreHorizontal, Sparkles } from 'lucide-react';
import type { Assistant } from '../types';

interface ChatHeaderProps { assistant: Assistant; onMenu: () => void; }

export function ChatHeader({ assistant, onMenu }: ChatHeaderProps) {
  return <header className="chat-header"><button className="icon-button menu-button" onClick={onMenu} aria-label="Abrir menú"><Menu size={20} /></button><div className="assistant-heading"><span className="assistant-heading__icon"><Sparkles size={16} /></span><div><h1>{assistant.name}</h1><p><span className="status-dot" />{assistant.status}</p></div></div><button className="icon-button" aria-label="Más opciones"><MoreHorizontal size={20} /></button></header>;
}
