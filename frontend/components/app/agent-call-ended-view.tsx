import { CheckCircle } from 'lucide-react';
import { Button } from '@/components/ui/button';

interface AgentCallEndedViewProps {
  onStartCall: () => void;
  startButtonText: string;
  appConfig: any; // AppConfig type
}

export function AgentCallEndedView({
  onStartCall,
  startButtonText,
  appConfig
}: AgentCallEndedViewProps) {
  return (
    <div className="bg-background flex flex-col items-center justify-center text-center p-6">
      {/* Call Ended Icon */}
      <div className="mb-6">
        <CheckCircle
          className="h-10 w-10 text-accent"
        />
      </div>

      <h2 className="text-xl font-semibold text-foreground mb-4">
        Consultation Ended
      </h2>
      <p className="text-lg text-muted-foreground mb-6">
        Thank you for using the Health Access Voice Agent.
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
          Ready for another health consultation?
        </p>
      </div>

      {/* Optional: Show disclaimer */}
      <div className="mt-8 pt-4 border-t border-muted-transparent text-xs text-muted-foreground">
        <p className="whitespace-pre-line">
          This voice agent provides general health information only.
          For medical advice, diagnosis, or treatment, please consult a qualified healthcare professional.
        </p>
      </div>
    </div>
  );
}