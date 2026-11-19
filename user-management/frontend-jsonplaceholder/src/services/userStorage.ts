import type { User } from "../types/user";

const STORAGE_KEY = "users";

export function getSavedUsers(): User[] {
    const savedUsers = localStorage.getItem(STORAGE_KEY);

    if (!savedUsers) {
        return [];
    }

    try {
        return JSON.parse(savedUsers) as User[];
    } catch {
        return [];
    }
}

export function saveUsers(users: User[]): void {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(users));
}
