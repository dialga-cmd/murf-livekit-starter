import { Mic } from 'lucide-react';

interface AgentListeningViewProps {
  appConfig: any; // AppConfig type
}

export function AgentListeningView({
  appConfig
}: AgentListeningViewProps) {
  return (
    <div className="bg-background flex flex-col items-center justify-center text-center p-6">
      {/* Listening Icon with Visual Feedback */}
      <div className="relative mb-6">
        <Mic
          className="h-10 w-10 text-accent"
        />
        {/* Sound waves animation */}
        <div className="absolute inset-0 animate-pulse rounded-full border-2 border-accent/20"></div>
      </div>

      <h2 className="text-xl font-semibold text-foreground mb-4">
        Listening to you...
      </h2>
      <p className="text-lg text-muted-foreground mb-6">
        I'm here to help with your health questions. Please speak clearly.
      </p>

      <div className="space-y-3 text-center">
        <p className="flex items-center justify-center gap-2 text-sm text-muted-foreground">
          <span className="h-2 w-2 inline-block rounded-full bg-accent animate-pulse"></span>
          <span>Processing your speech...</span>
        </p>
        <p className="flex items-center justify-center gap-2 text-sm text-muted-foreground">
          <span className="h-2 w-2 inline-block rounded-full bg-accent animate-pulse"></span>
          <span>Understanding your health query...</span>
        </p>
      </div>

      {/* Optional: Show language indicator if needed */}
      <div className="mt-6 text-sm text-muted-foreground">
        <div className="flex items-center justify-center gap-2">
          <div className="h-2 w-2 rounded-full bg-muted"></div>
          <span>Listening in English</span>
        </div>
      </div>
    </div>
  );
}