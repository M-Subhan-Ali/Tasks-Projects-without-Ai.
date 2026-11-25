import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { ReactNode } from "react";

import { SESSION_EXPIRED_MESSAGE, setUnauthorizedHandler } from "../services/apiClient";
import * as authService from "../services/authService";
import type { Account, AuthStatus, Credentials } from "../types/auth";
import { createLogger } from "../utils/logger";
import { AuthContext } from "./AuthContext";

const log = createLogger("auth");

function AuthProvider({ children }: { children: ReactNode }) {
    const [account, setAccount] = useState<Account | null>(null);
    // The auth cookie is httpOnly, so JavaScript cannot tell whether one exists.
    // Every page load starts by asking the server: GET /auth/me.
    const [status, setStatus] = useState<AuthStatus>("checking");
    const [notice, setNotice] = useState<string>();

    // Read by the 401 handler, which is registered once and must see the latest status.
    const statusRef = useRef<AuthStatus>("checking");
    useEffect(() => {
        statusRef.current = status;
    }, [status]);

    // On page load: if the browser has a valid cookie, /auth/me returns the account.
    useEffect(() => {
        let isCancelled = false;

        authService
            .getCurrentAccount()
            .then((current) => {
                if (!isCancelled) {
                    log.info("Session restored from cookie", {
                        accountId: current.id,
                        role: current.role,
                    });
                    setAccount(current);
                    setStatus("authenticated");
                }
            })
            .catch(() => {
                // 401 (no cookie / expired) or network error: show the login page.
                if (!isCancelled) {
                    log.debug("No active session, showing the login page");
                    setStatus("anonymous");
                }
            });

        return () => {
            isCancelled = true;
        };
    }, []);

    // Any 401 ends the session. Only call it "expired" if the user was logged in;
    // a 401 for a wrong password or the first /auth/me check is not an expiry.
    useEffect(() => {
        setUnauthorizedHandler(() => {
            if (statusRef.current === "authenticated") {
                log.warn("Session expired (API returned 401), logging out");
                setAccount(null);
                setStatus("anonymous");
                setNotice(SESSION_EXPIRED_MESSAGE);
            }
        });

        return () => setUnauthorizedHandler(undefined);
    }, []);

    const login = useCallback(async (credentials: Credentials) => {
        // The server sets the httpOnly cookie and returns the account.
        const current = await authService.login(credentials);
        log.info("Logged in", { accountId: current.id, role: current.role });
        setAccount(current);
        setStatus("authenticated");
        setNotice(undefined);
    }, []);

    const logout = useCallback(async () => {
        try {
            await authService.logout(); // the server deletes the cookie
        } finally {
            log.info("Logged out");
            setAccount(null);
            setStatus("anonymous");
            setNotice("You have been logged out.");
        }
    }, []);

    const value = useMemo(
        () => ({ account, status, notice, login, logout }),
        [account, status, notice, login, logout]
    );

    return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export default AuthProvider;
