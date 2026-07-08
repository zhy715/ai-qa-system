import { useState, useRef, useEffect } from 'react';
import { Upload, FileText, Database, CheckCircle2, AlertCircle, Loader2 } from 'lucide-react';
import { uploadDocument, getDocuments } from '../api';

export default function Sidebar({ onRefresh }) {
  const [documents, setDocuments] = useState([]);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState('');
  const [llmReady, setLlmReady] = useState(null);
  const [chunks, setChunks] = useState(0);
  const fileInputRef = useRef(null);

  const fetchDocs = async () => {
    try {
      const data = await getDocuments();
      setDocuments(data.documents || []);
    } catch {
      // backend may not be running
    }
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

  useEffect(() => { fetchDocs(); fetchHealth(); }, []);

  const handleUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    if (!file.name.endsWith('.pdf')) {
      setError('仅支持 PDF 文件');
      return;
    }
    setError('');
    setUploading(true);
    try {
      await uploadDocument(file);
      await fetchDocs();
      await fetchHealth();
      if (onRefresh) onRefresh();
    } catch (err) {
      setError(err.message);
    } finally {
      setUploading(false);
    }
  };

  return (
    <aside style={styles.sidebar}>
      {/* Header */}
      <div style={styles.header}>
        <div style={styles.logo}>
          <Database size={22} color="var(--color-primary)" />
          <span style={styles.logoText}>知识库问答</span>
        </div>
        <div style={styles.statusRow}>
          {llmReady === null ? (
            <span style={styles.statusPill}>检查中…</span>
          ) : llmReady ? (
            <span style={{ ...styles.statusPill, ...styles.statusOk }}>
              <CheckCircle2 size={12} /> AI 就绪
            </span>
          ) : (
            <span style={{ ...styles.statusPill, ...styles.statusWarn }}>
              <AlertCircle size={12} /> 未配置 LLM
            </span>
          )}
          <span style={styles.chunkCount}>{chunks} 块</span>
        </div>
      </div>

      {/* Upload */}
      <div style={styles.section}>
        <input
          ref={fileInputRef}
          type="file"
          accept=".pdf"
          onChange={handleUpload}
          style={{ display: 'none' }}
        />
        <button
          style={styles.uploadBtn}
          onClick={() => fileInputRef.current?.click()}
          disabled={uploading}
        >
          {uploading ? (
            <Loader2 size={18} style={{ animation: 'spin 1s linear infinite' }} />
          ) : (
            <Upload size={18} />
          )}
          <span>{uploading ? '上传中…' : '上传 PDF 文档'}</span>
        </button>
        {error && <p style={styles.error}>{error}</p>}
      </div>

      {/* Document List */}
      <div style={styles.section}>
        <h2 style={styles.sectionTitle}>已上传文档</h2>
        {documents.length === 0 ? (
          <p style={styles.emptyText}>暂无文档，请上传 PDF</p>
        ) : (
          <ul style={styles.docList}>
            {documents.map((doc) => (
              <li key={doc.id} style={styles.docItem}>
                <FileText size={16} style={styles.docIcon} />
                <span style={styles.docName}>{doc.filename}</span>
              </li>
            ))}
          </ul>
        )}
      </div>

      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
    </aside>
  );
}

const styles = {
  sidebar: {
    width: 'var(--sidebar-width)',
    minWidth: 'var(--sidebar-width)',
    height: '100vh',
    background: 'var(--color-surface)',
    borderRight: '1px solid var(--color-border)',
    display: 'flex',
    flexDirection: 'column',
    padding: 'var(--space-6)',
    gap: 'var(--space-6)',
    overflowY: 'auto',
  },
  header: {
    display: 'flex',
    flexDirection: 'column',
    gap: 'var(--space-3)',
  },
  logo: {
    display: 'flex',
    alignItems: 'center',
    gap: 'var(--space-3)',
    fontSize: 'var(--text-lg)',
    fontWeight: 600,
    color: 'var(--color-ink)',
    letterSpacing: '-0.01em',
  },
  logoText: {},
  statusRow: {
    display: 'flex',
    alignItems: 'center',
    gap: 'var(--space-2)',
    flexWrap: 'wrap',
  },
  statusPill: {
    display: 'inline-flex',
    alignItems: 'center',
    gap: '4px',
    fontSize: 'var(--text-xs)',
    padding: '2px 8px',
    borderRadius: '100px',
    background: 'var(--color-border)',
    color: 'var(--color-muted)',
  },
  statusOk: {
    background: 'oklch(0.58 0.13 155 / 0.15)',
    color: 'oklch(0.45 0.11 155)',
  },
  statusWarn: {
    background: 'oklch(0.65 0.14 80 / 0.15)',
    color: 'oklch(0.50 0.12 80)',
  },
  chunkCount: {
    fontSize: 'var(--text-xs)',
    color: 'var(--color-muted)',
  },
  section: {
    display: 'flex',
    flexDirection: 'column',
    gap: 'var(--space-3)',
  },
  sectionTitle: {
    fontSize: 'var(--text-sm)',
    fontWeight: 600,
    color: 'var(--color-muted)',
    textTransform: 'uppercase',
    letterSpacing: '0.05em',
  },
  uploadBtn: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 'var(--space-2)',
    width: '100%',
    padding: 'var(--space-4) var(--space-5)',
    background: 'var(--color-primary)',
    color: '#fff',
    border: 'none',
    borderRadius: 'var(--radius-md)',
    fontSize: 'var(--text-sm)',
    fontWeight: 500,
    cursor: 'pointer',
    transition: `background var(--duration-fast) var(--ease-out)`,
  },
  error: {
    fontSize: 'var(--text-xs)',
    color: 'var(--color-error)',
  },
  emptyText: {
    fontSize: 'var(--text-sm)',
    color: 'var(--color-faint)',
    fontStyle: 'italic',
  },
  docList: {
    listStyle: 'none',
    display: 'flex',
    flexDirection: 'column',
    gap: 'var(--space-1)',
  },
  docItem: {
    display: 'flex',
    alignItems: 'center',
    gap: 'var(--space-3)',
    padding: 'var(--space-3) var(--space-4)',
    borderRadius: 'var(--radius-sm)',
    fontSize: 'var(--text-sm)',
    transition: `background var(--duration-fast)`,
    cursor: 'default',
  },
  docIcon: {
    color: 'var(--color-muted)',
    flexShrink: 0,
  },
  docName: {
    overflow: 'hidden',
    textOverflow: 'ellipsis',
    whiteSpace: 'nowrap',
  },
};
