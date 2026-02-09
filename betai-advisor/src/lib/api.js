const API = import.meta.env.VITE_API_URL || '/api';

async function request(path, options = {}) {
  const url = path.startsWith('http') ? path : `${API}${path}`;
  const res = await fetch(url, {
    ...options,
    headers: { 'Content-Type': 'application/json', ...options.headers },
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function sendMessage(message, sport, messages = []) {
  return request('/chat', {
    method: 'POST',
    body: JSON.stringify({ message, sport, messages }),
  });
}

export async function getChats(sport = null) {
  const q = sport ? `?sport=${encodeURIComponent(sport)}` : '';
  return request(`/chats${q}`);
}

export async function saveChat({ sport, title, messages, id, createdAt }) {
  return request('/chats', {
    method: 'POST',
    body: JSON.stringify({ sport, title, messages, id, createdAt }),
  });
}

export async function getSports() {
  return request('/sports');
}
