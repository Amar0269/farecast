const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:3000';

const buildUrl = (path) => {
  const base = API_BASE_URL.replace(/\/+$/, '');
  const normalizedPath = path.startsWith('/') ? path : `/${path}`;
  return `${base}${normalizedPath}`;
};

const request = async (path) => {
  const response = await fetch(buildUrl(path), {
    headers: {
      Accept: 'application/json',
    },
  });

  const payload = await response.json().catch(() => ({}));

  if (!response.ok || payload.success === false) {
    const message =
      payload?.message ||
      payload?.error ||
      `Request failed with status ${response.status}`;
    throw new Error(message);
  }

  return payload;
};

export const getStats = async () => {
  const payload = await request('/api/stats');
  return payload.data ?? {};
};

export const getLatestIndex = async () => {
  const payload = await request('/api/index');
  return payload.data ?? null;
};

export const getIndexHistory = async () => {
  const payload = await request('/api/index/history');
  return Array.isArray(payload.data) ? payload.data : [];
};

export const getLiveFares = async () => {
  const payload = await request('/api/fares/live');
  return Array.isArray(payload.data) ? payload.data : [];
};

export const getRoutes = async () => {
  const payload = await request('/api/routes');
  return Array.isArray(payload.data) ? payload.data : [];
};

export const getRoute = async (id) => {
  const payload = await request(`/api/routes/${id}`);
  return payload.data ?? null;
};

export const getAirlines = async () => {
  const payload = await request('/api/airlines');
  return Array.isArray(payload.data) ? payload.data : [];
};
