import { useState } from "react";
import type { SubmitEvent } from "react";
import { Link, Navigate, useLocation, useNavigate } from "react-router-dom";

import useAuth from "../hooks/useAuth";
import { getErrorMessage } from "../services/apiClient";

const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

interface LoginErrors {
    email?: string;
    password?: string;
}

function validate(email: string, password: string): LoginErrors {
    const errors: LoginErrors = {};

    if (!email.trim()) {
        errors.email = "Email is required.";
    } else if (!EMAIL_PATTERN.test(email.trim())) {
        errors.email = "Enter a valid email address.";
    }
    if (!password) {
        errors.password = "Password is required.";
    }

    return errors;
}

function LoginPage() {
    const { status, notice, login } = useAuth();
    const navigate = useNavigate();
    const location = useLocation();
    // Where the visitor was going before being sent here (see ProtectedRoute).
    const from = (location.state as { from?: string } | null)?.from ?? "/";

    const [email, setEmail] = useState("");
    const [password, setPassword] = useState("");
    const [errors, setErrors] = useState<LoginErrors>({});
    const [serverError, setServerError] = useState<string>();
    const [isSubmitting, setIsSubmitting] = useState(false);

    if (status === "authenticated") {
        return <Navigate to={from} replace />;
    }

    const handleSubmit = async (event: SubmitEvent<HTMLFormElement>) => {
        event.preventDefault();
        setServerError(undefined);

        const formErrors = validate(email, password);
        setErrors(formErrors);
        if (Object.keys(formErrors).length > 0) {
            return;
        }

        setIsSubmitting(true);
        try {
            await login({ email: email.trim(), password });
            navigate(from, { replace: true });
        } catch (error: unknown) {
            setServerError(getErrorMessage(error));
        } finally {
            setIsSubmitting(false);
        }
    };

    return (
        <div className="container auth-page">
            <h1>Log in</h1>

            {notice && !serverError && <p className="message info">{notice}</p>}
            {serverError && <p className="message error">{serverError}</p>}

            <form onSubmit={handleSubmit} noValidate>
                <div>
                    <label htmlFor="email">Email</label>
                    <input
                        id="email"
                        type="email"
                        autoComplete="username"
                        value={email}
                        onChange={(event) => setEmail(event.target.value)}
                    />
                    {errors.email && <span className="error-text">{errors.email}</span>}
                </div>

                <div>
                    <label htmlFor="password">Password</label>
                    <input
                        id="password"
                        type="password"
                        autoComplete="current-password"
                        value={password}
                        onChange={(event) => setPassword(event.target.value)}
                    />
                    {errors.password && (
                        <span className="error-text">{errors.password}</span>
                    )}
                </div>

                <button type="submit" disabled={isSubmitting}>
                    {isSubmitting ? "Logging in..." : "Log in"}
                </button>
            </form>

            <p>
                No account? <Link to="/register">Register</Link>
            </p>
        </div>
    );
}

export default LoginPage;
