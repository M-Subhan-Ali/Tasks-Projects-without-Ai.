import type { ReactNode } from "react";
import { Navigate, useLocation } from "react-router-dom";

import useAuth from "../hooks/useAuth";
import Loader from "./Loader";

// Only renders its children for a logged-in account; otherwise sends the
// visitor to /login and remembers where they wanted to go.
function ProtectedRoute({ children }: { children: ReactNode }) {
    const { status } = useAuth();
    const location = useLocation();

    if (status === "checking") {
        return <Loader message="Checking your session..." />;
    }

    if (status === "anonymous") {
        return <Navigate to="/login" replace state={{ from: location.pathname }} />;
    }

    return children;
}

export default ProtectedRoute;
