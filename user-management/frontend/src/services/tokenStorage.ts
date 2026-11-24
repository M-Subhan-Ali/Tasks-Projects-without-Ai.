// The access token lives in localStorage so a page refresh keeps you logged in.
// Trade-off: any JavaScript running on the page (e.g. injected by an XSS bug)
// can read it. An httpOnly cookie set by the server would be safer, because JS
// cannot read it at all, but it needs CSRF protection and backend changes.
const TOKEN_KEY = "accessToken";

export function getToken(): string | null {
    return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string): void {
    localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken(): void {
    localStorage.removeItem(TOKEN_KEY);
}
