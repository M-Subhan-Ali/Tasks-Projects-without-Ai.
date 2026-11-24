import type { ApiErrorResponse } from "../types/user";
import { clearToken, getToken } from "./tokenStorage";

// The ONE place that talks to the API: every request goes through request(),
// which adds the Authorization header and handles 401/403 the same way everywhere.

export const API_URL = import.meta.env.VITE_API_URL;

export const SESSION_EXPIRED_MESSAGE = "Session expired, please log in again.";
const FORBIDDEN_MESSAGE = "You don't have permission for this action.";

export class ApiError extends Error {
    status: number;

    constructor(message: string, status: number) {
        super(message);
        this.name = "ApiError";
        this.status = status;
    }
}

// AuthProvider registers a callback here, so a 401 anywhere logs the user out
// without every caller having to handle it.
let onSessionExpired: (() => void) | undefined;

export function setSessionExpiredHandler(handler: (() => void) | undefined): void {
    onSessionExpired = handler;
}

function getStatusMessage(status: number): string {
    switch (status) {
        case 400:
            return "Bad request. Please check the entered data.";
        case 404:
            return "Requested resource was not found.";
        case 409:
            return "This conflicts with existing data.";
        case 422:
            return "Some fields are invalid. Please check the form.";
        case 500:
            return "Server error. Please try again later.";
        default:
            return "Request failed. Please try again.";
    }
}

async function getResponseErrorMessage(response: Response): Promise<string> {
    try {
        const data = (await response.json()) as ApiErrorResponse;

        if (data.errors && data.errors.length > 0) {
            return data.errors
                .map((error) => `${error.field}: ${error.message}`)
                .join(" | ");
        }

        if (typeof data.detail === "string") {
            return data.detail;
        }
    } catch {
        return getStatusMessage(response.status);
    }

    return getStatusMessage(response.status);
}

export async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
    const token = getToken();
    const headers = new Headers(options.headers);

    if (token) {
        headers.set("Authorization", `Bearer ${token}`);
    }
    if (options.body) {
        headers.set("Content-Type", "application/json");
    }

    let response: Response;

    try {
        response = await fetch(`${API_URL}${path}`, { ...options, headers });
    } catch {
        throw new Error(
            "Cannot connect to the server. Please make sure the backend is running."
        );
    }

    // 401 with a token = the token is expired or invalid: log out.
    // 401 without a token (e.g. a wrong password at login) is a normal error.
    if (response.status === 401 && token) {
        clearToken();
        onSessionExpired?.();
        throw new ApiError(SESSION_EXPIRED_MESSAGE, 401);
    }

    if (response.status === 403) {
        throw new ApiError(FORBIDDEN_MESSAGE, 403);
    }

    if (!response.ok) {
        throw new ApiError(await getResponseErrorMessage(response), response.status);
    }

    if (response.status === 204) {
        return undefined as T;
    }

    return (await response.json()) as T;
}

export function getErrorMessage(error: unknown): string {
    return error instanceof Error ? error.message : "Something went wrong.";
}
