/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_OPENCLAW_URL: string;
  readonly VITE_OPENCLAW_TOKEN: string;
  readonly VITE_OPENCLAW_MODEL: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}