import type {
    User,
    UserFormData,
    UserListResponse,
    UserPayload,
    UserQuery,
} from "../types/user";
import { request } from "./apiClient";

function toPayload(formData: UserFormData): UserPayload {
    return {
        name: formData.name,
        email: formData.email,
        phone: formData.phone,
        city: formData.city || null,
        company: { name: formData.company },
    };
}

export function getUsers(query: UserQuery): Promise<UserListResponse> {
    const params = new URLSearchParams({
        page: String(query.page),
        limit: String(query.limit),
    });

    if (query.search) {
        params.set("search", query.search);
    }

    return request<UserListResponse>(`/users?${params.toString()}`);
}

export function createUser(formData: UserFormData): Promise<User> {
    return request<User>("/users", {
        method: "POST",
        body: JSON.stringify(toPayload(formData)),
    });
}

export function updateUser(id: number, formData: UserFormData): Promise<User> {
    return request<User>(`/users/${id}`, {
        method: "PUT",
        body: JSON.stringify(toPayload(formData)),
    });
}

export function deleteUser(id: number): Promise<void> {
    return request<void>(`/users/${id}`, { method: "DELETE" });
}
