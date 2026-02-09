// Production: your Render backend. Local dev: /api (Vite proxy to localhost:5000)
const API = import.meta.env.VITE_API_URL || (import.meta.env.DEV ? '/api' : 'https://betai-u72d.onrender.com');

const AUTH_TOKEN_KEY = 'betai-token';

export function getStoredToken() {
  try {
    return localStorage.getItem(AUTH_TOKEN_KEY)
  } catch (_) {}
  return null
}

export function setStoredToken(token) {
  try {
    if (token) localStorage.setItem(AUTH_TOKEN_KEY, token)
    else localStorage.removeItem(AUTH_TOKEN_KEY)
  } catch (_) {}
}

async function request(path, options = {}, requireAuth = false) {
  const url = path.startsWith('http') ? path : `${API}${path}`;
  const headers = { 'Content-Type': 'application/json', ...options.headers };
  const token = getStoredToken();
  if (token) headers['Authorization'] = `Bearer ${token}`;
  const res = await fetch(url, { ...options, headers });
  if (res.status === 401 && requireAuth) {
    setStoredToken(null)
    const err = new Error(await res.text().catch(() => 'Unauthorized'))
    err.status = 401
    throw err
  }
  if (!res.ok) throw new Error(await res.text().catch(() => 'Request failed'));
  return res.json();
}

export async function sendMessage(message, sport, messages = [], images = []) {
  return request('/chat', {
    method: 'POST',
    body: JSON.stringify({ message, sport, messages, images }),
  });
}

export async function getChats(sport = null) {
  const q = sport ? `?sport=${encodeURIComponent(sport)}` : '';
  return request(`/chats${q}`, {}, true);
}

export async function saveChat({ sport, title, messages, id, createdAt }) {
  return request('/chats', {
    method: 'POST',
    body: JSON.stringify({ sport, title, messages, id, createdAt }),
  }, true);
}

export async function login(email, password) {
  return request('/auth/login', {
    method: 'POST',
    body: JSON.stringify({ email, password }),
  });
}

export async function signup(email, password) {
  return request('/auth/signup', {
    method: 'POST',
    body: JSON.stringify({ email, password }),
  });
}

export async function authMe() {
  return request('/auth/me', {}, true);
}

export async function getSports() {
  return request('/sports');
}
