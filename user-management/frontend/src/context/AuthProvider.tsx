import { useCallback, useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";

import { SESSION_EXPIRED_MESSAGE, setSessionExpiredHandler } from "../services/apiClient";
import * as authService from "../services/authService";
import { clearToken, getToken, setToken } from "../services/tokenStorage";
import type { Account, AuthStatus, Credentials } from "../types/auth";
import { AuthContext } from "./AuthContext";

function AuthProvider({ children }: { children: ReactNode }) {
    const [account, setAccount] = useState<Account | null>(null);
    // With a saved token we must ask the server who we are before showing pages.
    const [status, setStatus] = useState<AuthStatus>(() =>
        getToken() ? "checking" : "anonymous"
    );
    const [notice, setNotice] = useState<string>();

    // On page load: turn a saved token back into the logged-in account.
    // An expired token gets a 401 here, which the session-expired handler handles.
    useEffect(() => {
        if (!getToken()) {
            return;
        }

        let isCancelled = false;

        authService
            .getCurrentAccount()
            .then((current) => {
                if (!isCancelled) {
                    setAccount(current);
                    setStatus("authenticated");
                }
            })
            .catch(() => {
                if (!isCancelled) {
                    setStatus("anonymous");
                }
            });

        return () => {
            isCancelled = true;
        };
    }, []);

    // Any request that gets a 401 with a token ends the session.
    useEffect(() => {
        setSessionExpiredHandler(() => {
            setAccount(null);
            setStatus("anonymous");
            setNotice(SESSION_EXPIRED_MESSAGE);
        });

        return () => setSessionExpiredHandler(undefined);
    }, []);

    const login = useCallback(async (credentials: Credentials) => {
        // Drop any stale token so a wrong password is not mistaken for an expired session.
        clearToken();
        const { access_token } = await authService.login(credentials);
        setToken(access_token);

        try {
            // The token only says who we are; /auth/me returns the current email and role.
            const current = await authService.getCurrentAccount();
            setAccount(current);
            setStatus("authenticated");
            setNotice(undefined);
        } catch (error: unknown) {
            clearToken();
            throw error;
        }
    }, []);

    const logout = useCallback(() => {
        clearToken();
        setAccount(null);
        setStatus("anonymous");
        setNotice("You have been logged out.");
    }, []);

    const value = useMemo(
        () => ({ account, status, notice, login, logout }),
        [account, status, notice, login, logout]
    );

    return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export default AuthProvider;
