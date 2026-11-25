import type { ApiErrorResponse } from "../types/user";
import { createLogger } from "../utils/logger";

const log = createLogger("api");
const REQUEST_ID_HEADER = "X-Request-ID";

// The ONE place that talks to the API: every request goes through request(),
// which sends the auth cookie and handles 401/403 the same way everywhere.
//
// The login token lives in an httpOnly cookie set by the backend. This code
// never sees it (JavaScript cannot read httpOnly cookies, so neither can an
// XSS attack); `credentials: "include"` just tells the browser to send it.

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
// without every caller having to handle it. AuthProvider decides whether the
// 401 means "session expired" (you were logged in) or just "not logged in".
let onUnauthorized: (() => void) | undefined;

export function setUnauthorizedHandler(handler: (() => void) | undefined): void {
    onUnauthorized = handler;
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
    const headers = new Headers(options.headers);
    const method = (options.method ?? "GET").toUpperCase();

    if (options.body) {
        headers.set("Content-Type", "application/json");
    }

    // Our own ID for this request. The backend reuses any valid UUID it gets in
    // X-Request-ID, so this same ID appears in the browser console, in the
    // Network tab and in the backend log: search for it to follow one request.
    const requestId = crypto.randomUUID();
    headers.set(REQUEST_ID_HEADER, requestId);

    const startedAt = performance.now();
    let response: Response;

    try {
        response = await fetch(`${API_URL}${path}`, {
            ...options,
            headers,
            credentials: "include", // send the auth cookie to the API (another port)
        });
    } catch (error: unknown) {
        log.error(`${method} ${path} failed: cannot reach the server`, { requestId, error });
        throw new Error(
            "Cannot connect to the server. Please make sure the backend is running.",
            { cause: error } // keep the original fetch error attached for debugging
        );
    }

    // Never log request or response bodies: they hold passwords and user data.
    const summary = `${method} ${path} ${response.status}`;
    const details = {
        requestId,
        durationMs: Math.round(performance.now() - startedAt),
    };

    if (response.ok) {
        log.debug(summary, details);
        return response.status === 204
            ? (undefined as T)
            : ((await response.json()) as T);
    }

    const message =
        response.status === 403
            ? FORBIDDEN_MESSAGE
            : await getResponseErrorMessage(response);

    if (response.status >= 500) {
        log.error(summary, { ...details, message });
    } else {
        log.warn(summary, { ...details, message });
    }

    if (response.status === 401) {
        onUnauthorized?.();
    }

    throw new ApiError(message, response.status);
}

export function getErrorMessage(error: unknown): string {
    return error instanceof Error ? error.message : "Something went wrong.";
}
