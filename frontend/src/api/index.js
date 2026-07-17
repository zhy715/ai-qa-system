/** API 请求层 — 开发走 Vite 代理，Docker 走 nginx 代理 */
import { API_BASE } from './config';

async function request(path, options = {}) {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...options.headers },
    ...options,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || `HTTP ${res.status}`);
  }
  return res.json();
}

/** 上传文档 */
export async function uploadDocument(file) {
  const formData = new FormData();
  formData.append('file', file);
  const res = await fetch(`${API_BASE}/upload`, {
    method: 'POST',
    body: formData,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || `Upload failed`);
  }
  return res.json();
}

/** 获取文档列表 */
export function getDocuments() {
  return request('/documents');
}

/** 删除文档 */
export function deleteDocument(filename) {
  return request(`/documents/${encodeURIComponent(filename)}`, { method: 'DELETE' });
}

/** RAG 问答（支持多轮对话） */
export function queryKnowledge(question, topK = 3, conversationId = null) {
  return request('/query', {
    method: 'POST',
    body: JSON.stringify({
      question,
      top_k: topK,
      conversation_id: conversationId,
    }),
  });
}

/** 对话管理 */
export function createConversation() {
  return request('/conversations', { method: 'POST' });
}
export function getConversations() {
  return request('/conversations');
}
export function getConversation(id) {
  return request(`/conversations/${id}`);
}
export function deleteConversation(id) {
  return request(`/conversations/${id}`, { method: 'DELETE' });
}

/** 健康检查 */
export function healthCheck() {
  return request('/health');
}
