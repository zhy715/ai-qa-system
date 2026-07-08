import { User, Sparkles } from 'lucide-react';

export default function ChatMessage({ message }) {
  const isUser = message.role === 'user';

  return (
    <div
      style={{
        ...styles.wrapper,
        justifyContent: isUser ? 'flex-end' : 'flex-start',
      }}
    >
      <div
        style={{
          ...styles.bubble,
          background: isUser
            ? 'var(--color-primary)'
            : 'var(--color-surface)',
          color: isUser ? '#fff' : 'var(--color-ink)',
          border: isUser ? 'none' : '1px solid var(--color-border)',
        }}
      >
        <div style={styles.avatar}>
          {isUser ? <User size={14} /> : <Sparkles size={14} />}
        </div>
        <div style={styles.content}>
          <p style={styles.text}>{message.content}</p>
          {message.sources && message.sources.length > 0 && (
            <div style={styles.sources}>
              {message.sources.map((s, i) => (
                <span key={i} style={styles.sourceTag}>{s}</span>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

const styles = {
  wrapper: {
    display: 'flex',
    padding: '0 var(--space-6)',
  },
  bubble: {
    display: 'flex',
    gap: 'var(--space-3)',
    maxWidth: '75%',
    padding: 'var(--space-4) var(--space-5)',
    borderRadius: 'var(--radius-lg)',
    borderBottomRightRadius: 'var(--space-2)',
    transition: `all var(--duration-fast) var(--ease-out)`,
  },
  avatar: {
    flexShrink: 0,
    width: 28,
    height: 28,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    borderRadius: '50%',
    background: 'oklch(0 0 0 / 0.1)',
  },
  content: {
    display: 'flex',
    flexDirection: 'column',
    gap: 'var(--space-2)',
    minWidth: 0,
  },
  text: {
    fontSize: 'var(--text-base)',
    lineHeight: 1.65,
    whiteSpace: 'pre-wrap',
    wordBreak: 'break-word',
  },
  sources: {
    display: 'flex',
    gap: 'var(--space-2)',
    flexWrap: 'wrap',
    paddingTop: 'var(--space-2)',
    borderTop: '1px solid oklch(0 0 0 / 0.08)',
  },
  sourceTag: {
    fontSize: 'var(--text-xs)',
    padding: '2px 8px',
    borderRadius: '100px',
    background: 'oklch(0 0 0 / 0.08)',
    color: 'var(--color-muted)',
  },
};
