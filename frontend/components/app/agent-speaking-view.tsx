import { Speaker } from 'lucide-react';

interface AgentSpeakingViewProps {
  appConfig: any; // AppConfig type
}

export function AgentSpeakingView({
  appConfig
}: AgentSpeakingViewProps) {
  return (
    <div className="bg-background flex flex-col items-center justify-center text-center p-6">
      {/* Speaking Icon with Visual Feedback */}
      <div className="relative mb-6">
        <Speaker
          className="h-10 w-10 text-accent"
        />
        {/* Sound waves animation for speaking */}
        <div className="absolute inset-0 animate-pulse rounded-full border-2 border-accent/20"></div>
      </div>

      <h2 className="text-xl font-semibold text-foreground mb-4">
        Agent is speaking...
      </h2>
      <p className="text-lg text-muted-foreground mb-6">
        Your health assistant is providing information...
      </p>

      <div className="space-y-3 text-center">
        <p className="flex items-center justify-center gap-2 text-sm text-muted-foreground">
          <div className="h-2 w-2 rounded-full bg-accent animate-pulse"></div>
          <span>Generating health response...</span>
        </p>
        <p className="flex items-center justify-center gap-2 text-sm text-muted-foreground">
          <div className="h-2 w-2 rounded-full bg-accent animate-pulse"></div>
          <span>Converting to speech with Murf Falcon...</span>
        </p>
      </div>

      {/* Optional: Show that it's speaking in the user's language */}
      <div className="mt-6 text-sm text-muted-foreground">
        <div className="flex items-center justify-center gap-2">
          <div className="h-2 w-2 rounded-full bg-muted"></div>
          <span>Speaking in English</span>
        </div>
      </div>
    </div>
  );
}