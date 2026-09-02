import { Bot, ChevronDown, LogOut, MessageSquarePlus, PanelLeftClose, Settings2 } from 'lucide-react';
import type { Conversation, User } from '../types';

interface SidebarProps {
  conversations: Conversation[];
  activeId: string;
  user: User;
  isOpen: boolean;
  onSelect: (id: string) => void;
  onNewChat: () => void;
  onLogout: () => void;
  onClose: () => void;
}

export function Sidebar({ conversations, activeId, user, isOpen, onSelect, onNewChat, onLogout, onClose }: SidebarProps) {
  const getInitials = (username: string) => {
    return username
      .split(' ')
      .map((word) => word[0])
      .join('')
      .toUpperCase()
      .slice(0, 2);
  };

  return (
    <aside className={`sidebar ${isOpen ? 'sidebar--open' : ''}`} aria-label="Barra lateral">
      <div className="sidebar__topline">
        <div className="brand">
          <span className="brand__mark">
            <Bot size={18} />
          </span>
          <span>ORION</span>
        </div>
        <button className="icon-button sidebar__close" onClick={onClose} aria-label="Cerrar menú">
          <PanelLeftClose size={18} />
        </button>
      </div>

      <button className="new-chat" onClick={onNewChat}>
        <MessageSquarePlus size={17} />
        <span>Nuevo chat</span>
        <kbd>⌘ K</kbd>
      </button>

      <div className="conversation-list">
        <div className="list-label">
          Recientes <span>{conversations.length}</span>
        </div>
        {conversations.map((conversation) => (
          <button
            key={conversation.id}
            className={`conversation ${conversation.id === activeId ? 'conversation--active' : ''}`}
            onClick={() => onSelect(conversation.id)}
          >
            <span className="conversation__icon">
              <MessageSquarePlus size={15} />
            </span>
            <span className="conversation__copy">
              <strong>{conversation.title}</strong>
              <small>{conversation.preview}</small>
            </span>
            <span className="conversation__time">{conversation.updatedAt}</span>
          </button>
        ))}
      </div>

      <div className="sidebar__footer">
        <div className="profile">
          <span className="avatar">{getInitials(user.username)}</span>
          <span className="profile__copy">
            <strong>{user.username}</strong>
            <small>@usuario</small>
          </span>
        </div>
        <button className="settings">
          <Settings2 size={16} />
          <span>Preferencias</span>
          <span className="status-dot" />
        </button>
        <button className="logout-btn" onClick={onLogout} title="Cerrar sesión">
          <LogOut size={16} />
          <span>Cerrar sesión</span>
        </button>
        <p className="version">
          ORION DESKTOP <span>v0.1</span>
        </p>
      </div>
    </aside>
  );
}
