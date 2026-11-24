import { createContext } from "react";

import type { Account, AuthStatus, Credentials } from "../types/auth";

export interface AuthContextValue {
    account: Account | null;
    status: AuthStatus;
    // Shown on the login page, e.g. after the session expired.
    notice: string | undefined;
    login: (credentials: Credentials) => Promise<void>;
    logout: () => void;
}

export const AuthContext = createContext<AuthContextValue | undefined>(undefined);
