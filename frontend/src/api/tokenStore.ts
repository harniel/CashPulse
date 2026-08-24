// The access token lives in a plain module-level variable, never in
// Redux/localStorage/sessionStorage (BLUEPRINT.md §13): it's short-lived
// (10 min) and held only in memory, so an XSS bug can steal at most one
// access token's worth of access, never the long-lived refresh token
// (which stays in an httpOnly cookie the JS layer can't read at all).
let accessToken: string | null = null;

export function getAccessToken(): string | null {
  return accessToken;
}

export function setAccessToken(token: string | null): void {
  accessToken = token;
}
