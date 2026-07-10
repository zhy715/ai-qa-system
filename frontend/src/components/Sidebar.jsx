import { useState, useRef, useEffect } from 'react';
import {
  Upload, FileText, Scale, CheckCircle2, AlertCircle, Loader2, Cloud,
  MessageSquare, Plus, Trash2,
} from 'lucide-react';
import { uploadDocument, getDocuments, getConversations, deleteConversation } from '../api';

const SIDEBAR_PX = 320;

const styles = {
  sidebar: {
    width: SIDEBAR_PX,
    minWidth: SIDEBAR_PX,
    height: '100vh',
    background: '#fafaf9',
    borderRight: '1px solid #e8e6e1',
    display: 'flex',
    flexDirection: 'column',
    padding: '24px 20px',
    gap: 24,
    overflowY: 'auto',
    fontFamily: "'Inter', system-ui, -apple-system, sans-serif",
  },
  header: {
    display: 'flex',
    flexDirection: 'column',
    gap: 10,
  },
  logo: {
    display: 'flex',
    alignItems: 'center',
    gap: 10,
    fontSize: 17,
    fontWeight: 600,
    color: '#1a1a1a',
    letterSpacing: '-0.01em',
  },
  statusRow: {
    display: 'flex',
    alignItems: 'center',
    gap: 8,
    flexWrap: 'wrap',
  },
  statusPill: {
    display: 'inline-flex',
    alignItems: 'center',
    gap: 4,
    fontSize: 11,
    padding: '3px 10px',
    borderRadius: 100,
    background: '#e8e6e1',
    color: '#78716c',
    fontWeight: 500,
  },
  statusOk: {
    background: '#e0f2e9',
    color: '#2d6a4f',
  },
  section: {
    display: 'flex',
    flexDirection: 'column',
    gap: 10,
  },
  sectionTitle: {
    fontSize: 11,
    fontWeight: 600,
    color: '#a8a29e',
    textTransform: 'uppercase',
    letterSpacing: '0.06em',
    margin: 0,
  },
  // Upload drop zone — BIG and OBVIOUS
  uploadZone: {
    border: '2px dashed #d6d3d1',
    borderRadius: 12,
    padding: '28px 16px',
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    gap: 10,
    cursor: 'pointer',
    background: '#fefefe',
    transition: 'all 150ms ease',
    textAlign: 'center',
  },
  uploadIconCircle: {
    width: 44,
    height: 44,
    borderRadius: '50%',
    background: 'oklch(0.58 0.16 45 / 0.10)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    color: 'oklch(0.58 0.16 45)',
  },
  uploadText: {
    fontSize: 14,
    fontWeight: 500,
    color: '#1a1a1a',
    margin: 0,
  },
  uploadHint: {
    fontSize: 12,
    color: '#a8a29e',
    margin: 0,
  },
  error: {
    fontSize: 12,
    color: '#dc2626',
    margin: 0,
    padding: '4px 8px',
    background: '#fef2f2',
    borderRadius: 6,
  },
  emptyText: {
    fontSize: 13,
    color: '#c4bfb8',
    fontStyle: 'italic',
    margin: 0,
    padding: '8px 0',
  },
  docList: {
    listStyle: 'none',
    display: 'flex',
    flexDirection: 'column',
    gap: 2,
    padding: 0,
  },
  docItem: {
    display: 'flex',
    alignItems: 'center',
    gap: 10,
    padding: '10px 12px',
    borderRadius: 8,
    fontSize: 13,
    color: '#44403c',
    transition: 'background 120ms',
    cursor: 'default',
  },
  docIcon: {
    color: '#a8a29e',
    flexShrink: 0,
  },
  docName: {
    overflow: 'hidden',
    textOverflow: 'ellipsis',
    whiteSpace: 'nowrap',
    fontWeight: 500,
  },
  // Conversation list
  sectionRow: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  newBtn: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    width: 28,
    height: 28,
    borderRadius: 8,
    border: 'none',
    background: 'transparent',
    color: '#a8a29e',
    cursor: 'pointer',
    transition: 'all 120ms',
  },
  convList: {
    listStyle: 'none',
    display: 'flex',
    flexDirection: 'column',
    gap: 2,
    padding: 0,
  },
  convItem: {
    display: 'flex',
    alignItems: 'center',
    gap: 8,
    padding: '8px 10px',
    borderRadius: 8,
    fontSize: 13,
    color: '#44403c',
    cursor: 'pointer',
    transition: 'background 120ms',
    position: 'relative',
  },
  convIcon: {
    color: '#a8a29e',
    flexShrink: 0,
  },
  convTitle: {
    flex: 1,
    overflow: 'hidden',
    textOverflow: 'ellipsis',
    whiteSpace: 'nowrap',
    fontWeight: 500,
  },
  convDate: {
    fontSize: 11,
    color: '#c4bfb8',
    flexShrink: 0,
  },
  deleteBtn: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    width: 22,
    height: 22,
    borderRadius: 6,
    border: 'none',
    background: 'transparent',
    color: '#c4bfb8',
    cursor: 'pointer',
    flexShrink: 0,
    opacity: 0,
    transition: 'all 120ms',
  },
};

export default function Sidebar({
  conversationId, onSelectConversation, onNewConversation,
  viewingDocument, onViewDocument, refreshSignal,
}) {
  const [documents, setDocuments] = useState([]);
  const [conversations, setConversations] = useState([]);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState('');
  const [llmReady, setLlmReady] = useState(null);
  const [chunks, setChunks] = useState(0);
  const [isDragOver, setIsDragOver] = useState(false);
  const fileInputRef = useRef(null);

  const fetchDocs = async () => {
    try {
      const data = await getDocuments();
      setDocuments(data.documents || []);
    } catch { /* backend may be down */ }
  };

  const fetchHealth = async () => {
    try {
      const res = await fetch('http://localhost:8000/health');
      const data = await res.json();
      setLlmReady(data.llm_ready);
      setChunks(data.chunks_stored || 0);
    } catch {
      setLlmReady(false);
    }
  };

  const fetchConvs = async () => {
    try {
      const data = await getConversations();
      setConversations(data.conversations || []);
    } catch { /* ok */ }
  };

  useEffect(() => { fetchDocs(); fetchHealth(); fetchConvs(); }, []);

  // ChatArea 产生新对话时，refreshSignal 递增 → 刷新对话列表
  useEffect(() => {
    fetchConvs();
  }, [refreshSignal]);

  const doUpload = async (file) => {
    if (!file) return;
    const allowedExts = ['.pdf', '.txt', '.md', '.docx', '.csv', '.html', '.htm'];
    const ext = '.' + file.name.split('.').pop().toLowerCase();
    if (!allowedExts.includes(ext)) {
      setError('仅支持 PDF / TXT / MD / DOCX / CSV / HTML');
      return;
    }
    setError('');
    setUploading(true);
    try {
      await uploadDocument(file);
      setError('');
      await fetchDocs();
      await fetchHealth();
    } catch (err) {
      setError(err.message || '上传失败');
    } finally {
      setUploading(false);
    }
  };

  const handleFileChange = (e) => doUpload(e.target.files?.[0]);

  const handleDrag = (e) => {
    e.preventDefault();
    e.stopPropagation();
  };
  const handleDragIn = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragOver(true);
  };
  const handleDragOut = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragOver(false);
  };
  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragOver(false);
    const file = e.dataTransfer?.files?.[0];
    doUpload(file);
  };

  const handleDeleteConv = async (e, id) => {
    e.stopPropagation();
    try {
      await deleteConversation(id);
      if (conversationId === id) onNewConversation();
      fetchConvs();
    } catch { /* ok */ }
  };

  const dateLabel = (iso) => {
    try {
      const d = new Date(iso);
      const now = new Date();
      const diff = now - d;
      if (diff < 3600000) return '刚刚';
      if (diff < 86400000) return `${Math.floor(diff / 3600000)} 小时前`;
      return d.toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' });
    } catch { return ''; }
  };

  return (
    <aside style={styles.sidebar}>
      {/* Header */}
      <div style={styles.header}>
        <div style={styles.logo}>
          <Scale size={20} color="oklch(0.58 0.16 45)" />
          <span>律答 AI</span>
        </div>
        <div style={styles.statusRow}>
          {llmReady === null ? (
            <span style={styles.statusPill}>连接中…</span>
          ) : llmReady ? (
            <span style={{ ...styles.statusPill, ...styles.statusOk }}>
              <CheckCircle2 size={11} /> AI 在线
            </span>
          ) : (
            <span style={styles.statusPill}>
              <AlertCircle size={11} /> LLM 未配置
            </span>
          )}
          <span style={{ fontSize: 11, color: '#a8a29e' }}>{chunks} 个文本块</span>
        </div>
      </div>

      {/* Conversations */}
      <div style={styles.section}>
        <div style={styles.sectionRow}>
          <h2 style={styles.sectionTitle}>对话历史</h2>
          <button style={styles.newBtn} onClick={onNewConversation} title="新建对话">
            <Plus size={16} />
          </button>
        </div>
        {conversations.length === 0 ? (
          <p style={styles.emptyText}>暂无对话</p>
        ) : (
          <ul style={styles.convList}>
            {conversations.map((conv) => (
              <li
                key={conv.id}
                style={{
                  ...styles.convItem,
                  background: conv.id === conversationId ? '#f0ede8' : 'transparent',
                }}
                onClick={() => onSelectConversation(conv.id)}
              >
                <MessageSquare size={14} style={styles.convIcon} />
                <span style={styles.convTitle}>{conv.title}</span>
                <span style={styles.convDate}>{dateLabel(conv.updated_at)}</span>
                <button
                  style={styles.deleteBtn}
                  onClick={(e) => handleDeleteConv(e, conv.id)}
                  title="删除"
                >
                  <Trash2 size={12} />
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>

      {/* Upload Zone */}
      <div style={styles.section}>
        <h2 style={styles.sectionTitle}>上传法律文件</h2>
        <input
          ref={fileInputRef}
          type="file"
          accept=".pdf,.txt,.md,.docx,.csv,.html,.htm"
          onChange={handleFileChange}
          style={{ display: 'none' }}
        />
        <div
          style={{
            ...styles.uploadZone,
            borderColor: isDragOver ? 'oklch(0.58 0.16 45)' : '#d6d3d1',
            background: isDragOver ? 'oklch(0.58 0.16 45 / 0.05)' : '#fefefe',
          }}
          onClick={() => fileInputRef.current?.click()}
          onDragEnter={handleDragIn}
          onDragLeave={handleDragOut}
          onDragOver={handleDrag}
          onDrop={handleDrop}
        >
          {uploading ? (
            <>
              <Loader2 size={28} style={{ color: 'oklch(0.58 0.16 45)', animation: 'spin 1s linear infinite' }} />
              <p style={styles.uploadText}>上传中…</p>
            </>
          ) : (
            <>
              <div style={styles.uploadIconCircle}>
                <Cloud size={24} />
              </div>
              <p style={styles.uploadText}>上传法律文件</p>
              <p style={styles.uploadHint}>PDF · DOCX · TXT · CSV · MD · HTML</p>
            </>
          )}
        </div>
        {error && <p style={styles.error}>{error}</p>}
      </div>

      {/* Document List */}
      <div style={styles.section}>
        <h2 style={styles.sectionTitle}>已上传法律文件</h2>
        {documents.length === 0 ? (
          <p style={styles.emptyText}>暂未上传任何法律文件</p>
        ) : (
          <ul style={styles.docList}>
            {documents.map((doc) => {
              const isActive = viewingDocument === doc.filename;
              return (
                <li
                  key={doc.id}
                  style={{
                    ...styles.docItem,
                    background: isActive ? '#f0ede8' : 'transparent',
                    cursor: 'pointer',
                  }}
                  onClick={() => onViewDocument(doc.filename)}
                  title="点击查看文档内容"
                >
                  <FileText size={14} style={{
                    ...styles.docIcon,
                    color: isActive ? 'oklch(0.58 0.16 45)' : '#a8a29e',
                  }} />
                  <span style={styles.docName}>{doc.filename}</span>
                </li>
              );
            })}
          </ul>
        )}
      </div>

      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
    </aside>
  );
}
