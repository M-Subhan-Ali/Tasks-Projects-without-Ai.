import type { User, UserFormData, UserPayload } from "../types/user";

const USERS_URL = "https://jsonplaceholder.typicode.com/users";

export class ApiError extends Error {
    status: number;

    constructor(message: string, status: number) {
        super(message);
        this.name = "ApiError";
        this.status = status;
    }
}

function getStatusMessage(status: number): string {
    switch (status) {
        case 400:
            return "Bad request. Please check the entered data.";
        case 401:
            return "Unauthorized. Please log in again.";
        case 403:
            return "Forbidden. You do not have permission for this action.";
        case 404:
            return "Requested resource was not found.";
        case 500:
            return "Server error. Please try again later.";
        default:
            return "Request failed. Please try again.";
    }
}

async function request<T>(url: string, options?: RequestInit): Promise<T> {
    let response: Response;

    try {
        response = await fetch(url, options);
    } catch {
        throw new Error("Network error. Please check your internet connection.");
    }

    if (!response.ok) {
        throw new ApiError(
            `${getStatusMessage(response.status)} (Status: ${response.status})`,
            response.status
        );
    }

    return (await response.json()) as T;
}

export function toPayload(formData: UserFormData): UserPayload {
    return {
        name: formData.name,
        email: formData.email,
        phone: formData.phone,
        company: { name: formData.company },
    };
}

export function getUsers(): Promise<User[]> {
    return request<User[]>(USERS_URL);
}

export function createUser(formData: UserFormData): Promise<User> {
    return request<User>(USERS_URL, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(toPayload(formData)),
    });
}

export function updateUser(
    id: number,
    formData: UserFormData
): Promise<User> {
    return request<User>(`${USERS_URL}/${id}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ id, ...toPayload(formData) }),
    });
}

export function getErrorMessage(error: unknown): string {
    return error instanceof Error ? error.message : "Something went wrong.";
}
