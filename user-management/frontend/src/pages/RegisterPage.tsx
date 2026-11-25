import { useState } from "react";
import type { SubmitEvent } from "react";
import { Link, Navigate, useNavigate } from "react-router-dom";

import useAuth from "../hooks/useAuth";
import { getErrorMessage } from "../services/apiClient";
import * as authService from "../services/authService";

const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
const MIN_PASSWORD_LENGTH = 8;
const MAX_PASSWORD_LENGTH = 128;

interface RegisterErrors {
    email?: string;
    password?: string;
    confirmPassword?: string;
}

function validate(email: string, password: string, confirmPassword: string): RegisterErrors {
    const errors: RegisterErrors = {};

    if (!email.trim()) {
        errors.email = "Email is required.";
    } else if (!EMAIL_PATTERN.test(email.trim())) {
        errors.email = "Enter a valid email address.";
    }

    if (password.length < MIN_PASSWORD_LENGTH) {
        errors.password = `Password must be at least ${MIN_PASSWORD_LENGTH} characters.`;
    } else if (password.length > MAX_PASSWORD_LENGTH) {
        errors.password = `Password must be at most ${MAX_PASSWORD_LENGTH} characters.`;
    }

    if (confirmPassword !== password) {
        errors.confirmPassword = "Passwords do not match.";
    }

    return errors;
}

function RegisterPage() {
    const { status, login } = useAuth();
    const navigate = useNavigate();

    const [email, setEmail] = useState("");
    const [password, setPassword] = useState("");
    const [confirmPassword, setConfirmPassword] = useState("");
    const [errors, setErrors] = useState<RegisterErrors>({});
    const [serverError, setServerError] = useState<string>();
    const [isSubmitting, setIsSubmitting] = useState(false);

    if (status === "authenticated") {
        return <Navigate to="/" replace />;
    }

    const handleSubmit = async (event: SubmitEvent<HTMLFormElement>) => {
        event.preventDefault();
        setServerError(undefined);

        const formErrors = validate(email, password, confirmPassword);
        setErrors(formErrors);
        if (Object.keys(formErrors).length > 0) {
            return;
        }

        setIsSubmitting(true);
        try {
            const credentials = { email: email.trim(), password };
            await authService.register(credentials);
            // Log straight in, so the new user does not have to type it all again.
            await login(credentials);
            navigate("/", { replace: true });
        } catch (error: unknown) {
            setServerError(getErrorMessage(error));
        } finally {
            setIsSubmitting(false);
        }
    };

    return (
        <div className="container auth-page">
            <h1>Create an account</h1>
            <p className="muted">
                New accounts are viewers: they can see users but not change them.
            </p>

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
                        autoComplete="new-password"
                        value={password}
                        onChange={(event) => setPassword(event.target.value)}
                    />
                    {errors.password && (
                        <span className="error-text">{errors.password}</span>
                    )}
                </div>

                <div>
                    <label htmlFor="confirmPassword">Repeat password</label>
                    <input
                        id="confirmPassword"
                        type="password"
                        autoComplete="new-password"
                        value={confirmPassword}
                        onChange={(event) => setConfirmPassword(event.target.value)}
                    />
                    {errors.confirmPassword && (
                        <span className="error-text">{errors.confirmPassword}</span>
                    )}
                </div>

                <button type="submit" className="btn-primary" disabled={isSubmitting}>
                    {isSubmitting ? "Creating account..." : "Register"}
                </button>
            </form>

            <p>
                Already have an account? <Link to="/login">Log in</Link>
            </p>
        </div>
    );
}

export default RegisterPage;
