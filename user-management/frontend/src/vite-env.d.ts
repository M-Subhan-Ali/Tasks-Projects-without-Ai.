interface ImportMetaEnv {
    readonly VITE_API_URL: string;
    // debug | info | warn | error. Optional: see src/utils/logger.ts for the default.
    readonly VITE_LOG_LEVEL?: string;
}

interface ImportMeta {
    readonly env: ImportMetaEnv;
}
