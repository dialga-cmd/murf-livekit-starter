import { ReactNode, useEffect } from 'react';
import { toast as sonnerToast } from 'sonner';
import { useAgent, useSessionContext } from '@livekit/components-react';
import { WarningIcon } from '@phosphor-icons/react';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';

interface ToastProps {
  title: ReactNode;
  description: ReactNode;
}

function toastAlert(toast: ToastProps) {
  const { title, description } = toast;

  return sonnerToast.custom(
    (id) => (
      <Alert onClick={() => sonnerToast.dismiss(id)} className="bg-accent w-full md:w-[364px]">
        <WarningIcon weight="bold" />
        <AlertTitle>{title}</AlertTitle>
        {description && <AlertDescription>{description}</AlertDescription>}
      </Alert>
    ),
    { duration: 10_000 }
  );
}

export function useAgentErrors() {
  const agent = useAgent();
  const { isConnected, end } = useSessionContext();

  useEffect(() => {
    if (isConnected && agent.state === 'failed') {
      const reasons = agent.failureReasons;

      // Check if this is a microphone permission error
      const isMicrophonePermissionError = reasons.some(reason =>
        reason.toLowerCase().includes('microphone') ||
        reason.toLowerCase().includes('permission') ||
        reason.toLowerCase().includes('notallowed') ||
        reason.toLowerCase().includes('notfound')
      );

      if (isMicrophonePermissionError) {
        toastAlert({
          title: 'Microphone Access Required',
          description: (
            <>
              <p className="mb-2">
                To use the health assistant, we need access to your microphone.
              </p>
              <p className="mb-4">
                Please click the lock icon in your browser's address bar and allow microphone access for this site.
              </p>
              <p className="text-sm">
                <a
                  target="_blank"
                  rel="noopener noreferrer"
                  href="https://support.google.com/chrome/answer/2693767"
                  className="underline"
                >
                  Learn how to enable microphone access
                </a>
              </p>
            </>
          ),
        });
      } else {
        toastAlert({
          title: 'Session ended',
          description: (
            <>
              {reasons.length > 1 && (
                <ul className="list-inside list-disc">
                  {reasons.map((reason) => (
                    <li key={reason}>{reason}</li>
                  ))}
                </ul>
              )}
              {reasons.length === 1 && <p className="w-full">{reasons[0]}</p>}
              <p className="w-full">
                <a
                  target="_blank"
                  rel="noopener noreferrer"
                  href="https://docs.livekit.io/agents/start/voice-ai/"
                  className="whitespace-nowrap underline"
                >
                  See quickstart guide
                </a>
                .
              </p>
            </>
          ),
        });
      }

      end();
    }
  }, [agent, isConnected, end]);
}
