// Reusable logger for the whole frontend.
//
// Usage, once per file:
//     const log = createLogger("auth");
//     log.info("Logged in", { accountId: 4 });
//
// Prints:  10:15:02.123 INFO [auth] Logged in  {accountId: 4}
//
// Why not console.log everywhere?
// - one format: every line has a time, a level and a scope (where it came from);
// - levels: debug lines show while developing and are hidden in production;
// - safety: keys like "password" or "token" are replaced by "[redacted]";
// - history: the last 200 entries are kept, so in development you can type
//   appLogs() in the DevTools console to see what happened before a bug.

export type LogLevel = "debug" | "info" | "warn" | "error";

export type LogContext = Record<string, unknown>;

export interface LogEntry {
    time: string;
    level: LogLevel;
    scope: string;
    message: string;
    context?: LogContext;
}

export interface Logger {
    debug: (message: string, context?: LogContext) => void;
    info: (message: string, context?: LogContext) => void;
    warn: (message: string, context?: LogContext) => void;
    error: (message: string, context?: LogContext) => void;
}

const LEVEL_ORDER: Record<LogLevel, number> = { debug: 10, info: 20, warn: 30, error: 40 };

function isLogLevel(value: unknown): value is LogLevel {
    return typeof value === "string" && Object.hasOwn(LEVEL_ORDER, value);
}

// VITE_LOG_LEVEL in .env wins. Otherwise: everything in development
// (npm run dev), only warnings and errors in a production build.
const configuredLevel = import.meta.env.VITE_LOG_LEVEL?.toLowerCase();
const MIN_LEVEL: LogLevel = isLogLevel(configuredLevel)
    ? configuredLevel
    : import.meta.env.DEV
      ? "debug"
      : "warn";

const SENSITIVE_KEY = /pass(word)?|token|secret|authorization|cookie/i;
const MAX_DEPTH = 4;

// Copy the context, hiding sensitive values and turning Errors into plain
// objects (an Error's message and stack are not enumerable, so they would
// otherwise show up as {}).
function sanitize(value: unknown, depth = 0): unknown {
    if (value instanceof Error) {
        return { name: value.name, message: value.message, stack: value.stack };
    }
    if (value === null || typeof value !== "object") {
        return value;
    }
    if (depth >= MAX_DEPTH) {
        return "[too deep]";
    }
    if (Array.isArray(value)) {
        return value.map((item) => sanitize(item, depth + 1));
    }

    return Object.fromEntries(
        Object.entries(value).map(([key, item]) => [
            key,
            SENSITIVE_KEY.test(key) ? "[redacted]" : sanitize(item, depth + 1),
        ])
    );
}

const MAX_HISTORY = 200;
const history: LogEntry[] = [];

export function getLogHistory(): LogEntry[] {
    return [...history];
}

function write(level: LogLevel, scope: string, message: string, context?: LogContext): void {
    if (LEVEL_ORDER[level] < LEVEL_ORDER[MIN_LEVEL]) {
        return;
    }

    const entry: LogEntry = { time: new Date().toISOString(), level, scope, message };
    if (context) {
        entry.context = sanitize(context) as LogContext;
    }

    history.push(entry);
    if (history.length > MAX_HISTORY) {
        history.shift();
    }

    // "2026-11-25T10:15:02.123Z" -> "10:15:02.123"
    const prefix = `${entry.time.slice(11, 23)} ${level.toUpperCase()} [${scope}]`;
    // console.debug lines only show in Chrome when the "Verbose" level is on.
    if (entry.context) {
        console[level](prefix, message, entry.context);
    } else {
        console[level](prefix, message);
    }
}

export function createLogger(scope: string): Logger {
    return {
        debug: (message, context) => write("debug", scope, message, context),
        info: (message, context) => write("info", scope, message, context),
        warn: (message, context) => write("warn", scope, message, context),
        error: (message, context) => write("error", scope, message, context),
    };
}

// Errors that nothing else caught: a crash in an event handler, or a promise
// rejected without a .catch(). Call once, at startup (main.tsx).
export function installGlobalErrorLogging(): void {
    const log = createLogger("window");

    window.addEventListener("error", (event) => {
        log.error("Uncaught error", {
            error: event.error ?? event.message,
            source: `${event.filename}:${event.lineno}:${event.colno}`,
        });
    });

    window.addEventListener("unhandledrejection", (event) => {
        log.error("Unhandled promise rejection", { reason: event.reason });
    });
}

declare global {
    interface Window {
        appLogs?: () => LogEntry[];
    }
}

// Development only: type appLogs() in the DevTools console.
if (import.meta.env.DEV) {
    window.appLogs = getLogHistory;
}
