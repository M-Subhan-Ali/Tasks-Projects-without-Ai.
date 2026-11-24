export type Role = "admin" | "viewer";

export interface Account {
    id: number;
    email: string;
    role: Role;
}

export interface TokenResponse {
    access_token: string;
    token_type: string;
    expires_in: number;
}

export interface Credentials {
    email: string;
    password: string;
}

export type AuthStatus = "checking" | "authenticated" | "anonymous";
