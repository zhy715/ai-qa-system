import { User, Sparkles } from 'lucide-react';

const USER_BG = '#e8602c';       // warm coral (oklch 0.58 0.16 45)
const ASSISTANT_BG = '#f5f5f4';  // light surface
const USER_TEXT = '#ffffff';
const ASSISTANT_TEXT = '#1c1917';
const BORDER = '#e8e6e1';

export default function ChatMessage({ message }) {
  const isUser = message.role === 'user';

  return (
    <div style={{
      display: 'flex',
      justifyContent: isUser ? 'flex-end' : 'flex-start',
      padding: '4px 24px',
    }}>
      <div style={{
        display: 'flex',
        gap: 10,
        maxWidth: '75%',
        padding: '14px 18px',
        borderRadius: isUser ? '16px 16px 4px 16px' : '16px 16px 16px 4px',
        background: isUser ? USER_BG : ASSISTANT_BG,
        color: isUser ? USER_TEXT : ASSISTANT_TEXT,
        border: isUser ? 'none' : `1px solid ${BORDER}`,
      }}>
        <div style={{
          flexShrink: 0,
          width: 26,
          height: 26,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          borderRadius: '50%',
          background: isUser ? 'rgba(255,255,255,0.2)' : 'rgba(0,0,0,0.06)',
          color: isUser ? '#fff' : '#78716c',
        }}>
          {isUser ? <User size={13} /> : <Sparkles size={13} />}
        </div>
        <div style={{ minWidth: 0 }}>
          <p style={{
            margin: 0,
            fontSize: 15,
            lineHeight: 1.7,
            whiteSpace: 'pre-wrap',
            wordBreak: 'break-word',
          }}>
            {message.content}
          </p>
          {message.sources && message.sources.length > 0 && (
            <div style={{
              display: 'flex',
              gap: 6,
              flexWrap: 'wrap',
              marginTop: 10,
              paddingTop: 10,
              borderTop: `1px solid rgba(0,0,0,0.08)`,
            }}>
              {message.sources.map((s, i) => (
                <span key={i} style={{
                  fontSize: 11,
                  padding: '2px 8px',
                  borderRadius: 100,
                  background: 'rgba(0,0,0,0.06)',
                  color: '#78716c',
                }}>{s}</span>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
