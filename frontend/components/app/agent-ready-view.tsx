import { Button } from '@/components/ui/button';

interface AgentReadyViewProps {
  onStartCall: () => void;
  startButtonText: string;
  appConfig: any; // AppConfig type
}

export function AgentReadyView({
  onStartCall,
  startButtonText,
  appConfig
}: AgentReadyViewProps) {
  return (
    <div className="bg-background flex flex-col items-center justify-center text-center p-6">
      {/* Health Access Logo/Icon */}
      <div className="mb-8">
        {appConfig.logo ? (
          <img
            src={appConfig.logo}
            alt={`${appConfig.companyName} logo`}
            className="h-12 w-auto"
          />
        ) : (
          <div className="text-foreground h-12 w-12 flex items-center justify-center rounded-full bg-accent/20 text-accent">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
              <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 18c-4.41 0-8-3.59-8-8s3.59-8 8-8 8 3.59 8 8-3.59 8-8 8zm0-14c-2.21 0-4 1.79-4 4h2c0-1.1.9-2 2-2s2 .9 2 2h2c0-2.21-1.79-4-4-4z" fill="currentColor"/>
              <path d="M12 14c-2.21 0-4 1.79-4 4h2c0-1.1.9-2 2-2s2 .9 2 2h2c0-2.21-1.79-4-4-4zm-4 6h-2v-1h2v1zm0-4h-2v-1h2v1zm4 4h-2v-2h2v2z" fill="currentColor"/>
            </svg>
          </div>
        )}
      </div>

      <h1 className="text-2xl font-bold text-foreground mb-4">
        {appConfig.companyName}
      </h1>
      <p className="text-lg text-muted-foreground mb-6 max-w-xl">
        {appConfig.pageDescription}
      </p>

      <div className="space-y-4">
        <Button
          onClick={onStartCall}
          variant="default"
          className="w-64 h-12 rounded-full font-mono text-xs font-bold tracking-wider uppercase bg-accent text-accent-foreground hover:bg-accent/90"
        >
          {startButtonText}
        </Button>

        <p className="text-sm text-muted-foreground">
          Click to begin your health consultation
        </p>
      </div>
    </div>
  );
}