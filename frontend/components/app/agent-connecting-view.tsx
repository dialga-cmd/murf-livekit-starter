import { Loader2 } from 'lucide-react';

interface AgentConnectingViewProps {
  appConfig: any; // AppConfig type
}

export function AgentConnectingView({
  appConfig
}: AgentConnectingViewProps) {
  return (
    <div className="bg-background flex flex-col items-center justify-center text-center p-6">
      {/* Connecting Icon */}
      <div className="mb-6">
        <Loader2
          className="h-8 w-8 animate-spin text-accent"
        />
      </div>

      <h2 className="text-xl font-semibold text-foreground mb-4">
        Connecting to your health assistant...
      </h2>
      <p className="text-lg text-muted-foreground mb-8">
        Please wait while we establish a secure connection.
      </p>

      <div className="space-y-2 text-sm">
        <p className="flex items-center justify-center gap-2 text-muted-foreground">
          <div className="h-2 w-2 rounded-full bg-accent animate-pulse"></div>
          <span>Initializing voice pipeline...</span>
        </p>
        <p className="flex items-center justify-center gap-2 text-muted-foreground">
          <div className="h-2 w-2 rounded-full bg-accent animate-pulse"></div>
          <span>Connecting to Murf Falcon TTS...</span>
        </p>
        <p className="flex items-center justify-center gap-2 text-muted-foreground">
          <div className="h-2 w-2 rounded-full bg-accent animate-pulse"></div>
          <span>Preparing health knowledge base...</span>
        </p>
      </div>
    </div>
  );
}