import { Button } from '@/components/ui/button';

function WelcomeImage() {
  return (
    <svg
      width="64"
      height="64"
      viewBox="0 0 64 64"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className="text-fg0 mb-4 size-16"
    >
      {/* Healthcare cross symbol */}
      <rect x="28" y="12" width="8" height="40" fill="#10B981"/>
      <rect x="12" y="28" width="40" height="8" fill="#10B981"/>
      {/* Outer ring */}
      <circle cx="32" cy="32" r="30" stroke="#10B981" stroke-width="1.5"/>
    </svg>
  );
}

interface WelcomeViewProps {
  startButtonText: string;
  onStartCall: () => void;
  appConfig: any; // AppConfig type
}

export const WelcomeView = ({
  startButtonText,
  onStartCall,
  ref,
  appConfig,
}: React.ComponentProps<'div'> & WelcomeViewProps) => {
  return (
    <div ref={ref}>
      <section className="bg-background flex flex-col items-center justify-center text-center p-6">
        <div className="mb-4">
          {appConfig.logo ? (
            <img
              src={appConfig.logo}
              alt={`${appConfig.companyName} logo`}
              className="h-10 w-auto"
            />
          ) : (
            <WelcomeImage />
          )}
        </div>

        <h1 className="text-xl font-bold text-foreground mb-2">
          {appConfig.companyName}
        </h1>
        <p className="text-lg text-muted-foreground mb-4 max-w-xl">
          {appConfig.pageDescription}
        </p>

        <Button
          onClick={onStartCall}
          size="lg"
          className="w-64 rounded-full font-mono text-xs font-bold tracking-wider uppercase bg-accent text-accent-foreground hover:bg-accent/90"
        >
          {startButtonText}
        </Button>

        <p className="text-sm text-muted-foreground mt-2">
          Press the button above to begin your health consultation
        </p>
      </section>

      <div className="fixed bottom-5 left-0 flex w-full items-center justify-center">
        <p className="text-muted-foreground max-w-prose pt-1 text-xs leading-5 font-normal text-pretty md:text-sm">
          Need help getting set up? Check out the{' '}
          <a
            target="_blank"
            rel="noopener noreferrer"
            href="https://docs.livekit.io/agents/start/voice-ai/"
            className="underline"
          >
            Voice AI quickstart
          </a>
          .
        </p>
      </div>
    </div>
  );
};