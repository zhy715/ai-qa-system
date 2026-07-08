import { useState, useRef, useEffect } from 'react';
import { Send, Loader2, MessageSquare } from 'lucide-react';
import ChatMessage from './ChatMessage';
import { queryKnowledge, getConversation } from '../api';

export default function ChatArea({ conversationId, onConversationCreated }) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [currentConvId, setCurrentConvId] = useState(conversationId);
  const messagesEndRef = useRef(null);
  // 标记：是否由内部发送消息触发的 conversation 变更（避免重复加载覆盖消息）
  const internalCreateRef = useRef(false);

  // 外部切换对话时重新加载
  useEffect(() => {
    // 内部创建的新对话 → 消息已由 handleSend 添加，不要覆盖
    if (internalCreateRef.current) {
      internalCreateRef.current = false;
      return;
    }
    setCurrentConvId(conversationId);
    if (conversationId) {
      loadConversation(conversationId);
    } else {
      setMessages([]);
    }
  }, [conversationId]);

  const loadConversation = async (id) => {
    try {
      const data = await getConversation(id);
      setMessages(data.messages || []);
    } catch {
      setMessages([]);
    }
  };

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };
  useEffect(scrollToBottom, [messages]);

  const handleSend = async () => {
    const question = input.trim();
    if (!question || loading) return;

    // Add user message
    const userMsg = { role: 'user', content: question };
    setMessages((prev) => [...prev, userMsg]);
    setInput('');
    setLoading(true);

    try {
      const data = await queryKnowledge(question, 3, currentConvId);

      // 首次发送时后端创建新对话，返回 conversation_id
      if (data.conversation_id && !currentConvId) {
        setCurrentConvId(data.conversation_id);
        internalCreateRef.current = true;  // 阻止 useEffect 重复加载
        if (onConversationCreated) onConversationCreated(data.conversation_id);
      }

      const isFallback = data.answer.startsWith('⚠️ 请配置') || data.answer.startsWith('⚠️ LLM');

      const botMsg = {
        role: 'assistant',
        content: data.answer,
        sources: data.sources || [],
        isFallback,
      };
      setMessages((prev) => [...prev, botMsg]);
    } catch (err) {
      const errorMsg = {
        role: 'assistant',
        content: `❌ 请求失败：${err.message}\n\n请确认后端服务已启动（http://localhost:8000）`,
        sources: [],
        isError: true,
      };
      setMessages((prev) => [...prev, errorMsg]);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div style={styles.container}>
      {/* Messages */}
      <div style={styles.messagesArea}>
        {messages.length === 0 ? (
          <div style={styles.welcome}>
            <div style={styles.welcomeIcon}>
              <MessageSquare size={40} strokeWidth={1.5} />
            </div>
            <h1 style={styles.welcomeTitle}>开始提问</h1>
            <p style={styles.welcomeText}>
              上传 PDF 文档后，在此输入问题<br />
              系统会从知识库中检索相关内容并生成回答
            </p>
            <div style={styles.tips}>
              <span style={styles.tip}>💡 试试：</span>
              {['这份文档讲了什么？', '总结核心要点', '有哪些关键概念？'].map((q) => (
                <button
                  key={q}
                  style={styles.tipBtn}
                  onClick={() => setInput(q)}
                >
                  {q}
                </button>
              ))}
            </div>
          </div>
        ) : (
          messages.map((msg, i) => <ChatMessage key={i} message={msg} />)
        )}
        {loading && (
          <div style={styles.typing}>
            <Loader2 size={18} style={{ animation: 'spin 1s linear infinite' }} />
            <span>思考中…</span>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div style={styles.inputBar}>
        <div style={styles.inputWrapper}>
          <textarea
            style={styles.textarea}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="输入你的问题… (Enter 发送)"
            rows={1}
            disabled={loading}
          />
          <button
            style={{
              ...styles.sendBtn,
              opacity: input.trim() && !loading ? 1 : 0.4,
              cursor: input.trim() && !loading ? 'pointer' : 'default',
            }}
            onClick={handleSend}
            disabled={!input.trim() || loading}
          >
            <Send size={18} />
          </button>
        </div>
      </div>

      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
    </div>
  );
}

const styles = {
  container: {
    flex: 1,
    display: 'flex',
    flexDirection: 'column',
    height: '100vh',
    background: 'var(--color-bg)',
  },
  messagesArea: {
    flex: 1,
    overflowY: 'auto',
    display: 'flex',
    flexDirection: 'column',
    gap: 'var(--space-4)',
    padding: 'var(--space-6) 0',
  },
  welcome: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    flex: 1,
    gap: 'var(--space-4)',
    padding: 'var(--space-10)',
    textAlign: 'center',
  },
  welcomeIcon: {
    width: 80,
    height: 80,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    borderRadius: '50%',
    background: 'oklch(0.58 0.16 45 / 0.08)',
    color: 'var(--color-primary)',
    marginBottom: 'var(--space-2)',
  },
  welcomeTitle: {
    fontSize: 'var(--text-2xl)',
    fontWeight: 600,
    color: 'var(--color-ink)',
    letterSpacing: '-0.02em',
  },
  welcomeText: {
    fontSize: 'var(--text-base)',
    color: 'var(--color-muted)',
    lineHeight: 1.7,
    maxWidth: 360,
  },
  tips: {
    display: 'flex',
    flexWrap: 'wrap',
    gap: 'var(--space-2)',
    justifyContent: 'center',
    marginTop: 'var(--space-4)',
  },
  tip: {
    fontSize: 'var(--text-sm)',
    color: 'var(--color-muted)',
    width: '100%',
  },
  tipBtn: {
    fontSize: 'var(--text-sm)',
    padding: 'var(--space-2) var(--space-4)',
    border: '1px solid var(--color-border)',
    borderRadius: '100px',
    background: 'var(--color-bg)',
    color: 'var(--color-ink)',
    cursor: 'pointer',
    transition: `all var(--duration-fast) var(--ease-out)`,
  },
  typing: {
    display: 'flex',
    alignItems: 'center',
    gap: 'var(--space-2)',
    padding: 'var(--space-4) var(--space-6)',
    fontSize: 'var(--text-sm)',
    color: 'var(--color-muted)',
  },
  inputBar: {
    padding: 'var(--space-4) var(--space-6) var(--space-6)',
    borderTop: '1px solid var(--color-border)',
  },
  inputWrapper: {
    display: 'flex',
    alignItems: 'flex-end',
    gap: 'var(--space-3)',
    padding: 'var(--space-2) var(--space-2) var(--space-2) var(--space-4)',
    border: '1px solid var(--color-border)',
    borderRadius: 'var(--radius-lg)',
    background: 'var(--color-surface)',
    transition: `border-color var(--duration-fast)`,
  },
  textarea: {
    flex: 1,
    border: 'none',
    outline: 'none',
    background: 'transparent',
    fontSize: 'var(--text-base)',
    fontFamily: 'var(--font-sans)',
    color: 'var(--color-ink)',
    resize: 'none',
    padding: 'var(--space-2) 0',
    lineHeight: 1.5,
  },
  sendBtn: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    width: 40,
    height: 40,
    borderRadius: 'var(--radius-md)',
    border: 'none',
    background: 'var(--color-primary)',
    color: '#fff',
    transition: `all var(--duration-fast) var(--ease-out)`,
  },
};
