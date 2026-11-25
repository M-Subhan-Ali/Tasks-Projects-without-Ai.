import { Component } from "react";
import type { ErrorInfo, ReactNode } from "react";

import { createLogger } from "../utils/logger";

const log = createLogger("react");

interface ErrorBoundaryProps {
    children: ReactNode;
}

interface ErrorBoundaryState {
    hasError: boolean;
}

// If any component below this throws while rendering, React would normally
// unmount the whole app and leave a blank page. This catches the error, logs
// it with the component stack (which component crashed), and shows a message.
//
// It has to be a class: React has no hook for catching render errors.
// It does NOT catch errors in event handlers or promises; those are logged
// by installGlobalErrorLogging() in utils/logger.ts.
class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
    state: ErrorBoundaryState = { hasError: false };

    static getDerivedStateFromError(): ErrorBoundaryState {
        return { hasError: true };
    }

    componentDidCatch(error: Error, info: ErrorInfo): void {
        log.error("A component crashed while rendering", {
            error,
            componentStack: info.componentStack,
        });
    }

    render() {
        if (this.state.hasError) {
            return (
                <div className="container">
                    <p className="message error">
                        Something went wrong. Please reload the page.
                    </p>
                    <button onClick={() => window.location.reload()}>Reload</button>
                </div>
            );
        }

        return this.props.children;
    }
}

export default ErrorBoundary;
