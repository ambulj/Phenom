export {};

declare global {
  namespace JSX {
    interface IntrinsicElements {
      webview: React.DetailedHTMLProps<React.HTMLAttributes<HTMLElement>, HTMLElement> & {
        src?: string;
        partition?: string;
        allowpopups?: boolean | string;
        webpreferences?: string;
      };
    }
  }

  interface Window {
    phenom?: {
      getSessionToken: () => string;
      isFirstRunDone?: () => boolean;
      setFirstRunDone?: () => boolean;
      isVoiceMuted?: () => boolean;
      setVoiceMuted?: (muted: boolean) => boolean;
      onVoiceMutedChanged?: (callback: (muted: boolean) => void) => void;
      triggerGuardianKill?: () => void;
      onGuardianHotkey?: (callback: () => void) => void;
      muteAllAudio?: (muted: boolean) => Promise<boolean>;
      onMediaTransportKey?: (callback: (action: string) => void) => void;
      onMediaGuardianMute?: (callback: () => void) => void;
    };
  }
}
