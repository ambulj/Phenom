export {};

declare global {
  interface Window {
    phenom?: {
      getSessionToken: () => string;
    };
  }
}
