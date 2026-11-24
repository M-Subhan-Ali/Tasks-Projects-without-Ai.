import type { Account, Credentials } from "../types/auth";
import { request } from "./apiClient";

// The backend sets the httpOnly auth cookie and returns the account.
export function login(credentials: Credentials): Promise<Account> {
    return request<Account>("/auth/login", {
        method: "POST",
        body: JSON.stringify(credentials),
    });
}

export function register(credentials: Credentials): Promise<Account> {
    return request<Account>("/auth/register", {
        method: "POST",
        body: JSON.stringify(credentials),
    });
}

export function getCurrentAccount(): Promise<Account> {
    return request<Account>("/auth/me");
}

// Only the server can delete an httpOnly cookie.
export function logout(): Promise<void> {
    return request<void>("/auth/logout", { method: "POST" });
}
