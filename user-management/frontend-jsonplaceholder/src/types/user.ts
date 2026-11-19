export interface Company {
    name: string;
}

export interface User {
    id: number;
    name: string;
    email: string;
    phone: string;
    company: Company;
    isLocal?: boolean;
}

export type UserPayload = Omit<User, "id" | "isLocal">;

export interface UserFormData {
    name: string;
    email: string;
    phone: string;
    company: string;
}

export type FormErrors = Partial<Record<keyof UserFormData, string>>;

export type LoadStatus = "loading" | "success" | "error";

export type MessageType = "success" | "error";

export interface StatusMessage {
    type: MessageType;
    text: string;
}
