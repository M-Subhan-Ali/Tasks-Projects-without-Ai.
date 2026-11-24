import type { Account, Credentials, TokenResponse } from "../types/auth";
import { request } from "./apiClient";

export function login(credentials: Credentials): Promise<TokenResponse> {
    return request<TokenResponse>("/auth/login", {
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
