// Only the public server origin is stored here; credentials remain in session cookies.
export const readServer = async () => localStorage.getItem('attendance-server');
export const writeServer = async (origin: string) => { localStorage.setItem('attendance-server', origin); };
