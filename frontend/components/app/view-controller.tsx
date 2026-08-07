'use client';

import { useTheme } from 'next-themes';
import { AnimatePresence, motion } from 'motion/react';
import { useSessionContext, useAgent } from '@livekit/components-react';
import type { AppConfig } from '@/app-config';
import type { AgentState } from '@livekit/components-react';
import { WelcomeView } from '@/components/app/welcome-view';
import { AgentConnectingView } from '@/components/app/agent-connecting-view';
import { AgentListeningView } from '@/components/app/agent-listening-view';
import { AgentSpeakingView } from '@/components/app/agent-speaking-view>;
import { AgentCallEndedView } from '@/components/app/agent-call-ended-view>;
import { AgentReadyView } from '@/components/app/agent-ready-view>;

const MotionView = motion.create('div');

const VIEW_MOTION_PROPS = {
  variants: {
    visible: {
      opacity: 1,
    },
    hidden: {
      opacity: 0,
    },
  },
  initial: 'hidden',
  animate: 'visible',
  exit: 'hidden',
  transition: {
    duration: 0.5,
    ease: 'linear',
  },
};

interface ViewControllerProps {
  appConfig: AppConfig;
}

export function ViewController({ appConfig }: ViewControllerProps) {
  const { isConnected, start, end } = useSessionContext();
  const agent = useAgent();
  const { resolvedTheme } = useTheme();

  // Determine which view to show based on agent state
  const isReadyView = agent.state === 'idle' && !agent.isConnected;
  const isConnectingView = agent.state === 'connecting' || agent.state === 'pre-connect-buffering';
  const isListeningView = agent.state === 'listening';
  const isSpeakingView = agent.state === 'speaking';
  const isCallEndedView = agent.state === 'disconnected' && agent.isFinished;
  const isFailedView = agent.state === 'failed';

  return (
    <AnimatePresence mode="wait">
      {/* Ready view - show when agent is idle and not connected */}
      {isReadyView && (
        <MotionView
          key="ready"
          {...VIEW_MOTION_PROPS}
        >
          <AgentReadyView
            onStartCall={start}
            startButtonText={appConfig.startButtonText}
            appConfig={appConfig}
          />
        </MotionView>
      )}
      {/* Connecting view - show when connecting or buffering */}
      {isConnectingView && (
        <MotionView
          key="connecting"
          {...VIEW_MOTION_PROPS}
        >
          <AgentConnectingView
            appConfig={appConfig}
          />
        </MotionView>
      )}
      {/* Listening view - show when agent is listening */}
      {isListeningView && (
        <MotionView
          key="listening"
          {...VIEW_MOTION_PROPS}
        >
          <AgentListeningView
            appConfig={appConfig}
          />
        </MotionView>
      )}
      {/* Speaking view - show when agent is speaking */}
      {isSpeakingView && (
        <MotionView
          key="speaking"
          {...VIEW_MOTION_PROPS}
        >
          <AgentSpeakingView
            appConfig={appConfig}
          />
        </MotionView>
      )}
      {/* Call ended view - show when disconnected and finished */}
      {isCallEndedView && (
        <MotionView
          key="call-ended"
          {...VIEW_MOTION_PROPS}
        >
          <AgentCallEndedView
            onStartCall={start}
            startButtonText={appConfig.startButtonText}
            appConfig={appConfig}
          />
        </MotionView>
      )}
      {/* Failed view - show when connection failed */}
      {isFailedView && (
        <MotionView
          key="failed"
          {...VIEW_MOTION_PROPS}
        >
          <div className="text-center py-12">
            <p className="text-destructive">Microphone access is required for voice consultation.</p>
            <p className="text-muted-foreground mt-2">
              To enable microphone access:<br/>
              • Chrome/Firefox: Click the camera icon in address bar → Allow microphone<br/>
              • Safari: Safari → Settings for This Website → Microphone → Allow<br/>
              • Mobile: Settings → [Browser Name] → Microphone → Allow
            </p>
            <button
              onClick={(e) => start()}
              className="mt-6 btn btn-primary"
            >
              Try Again
            </button>
          </div>
        </MotionView>
      )}
      {/* Fallback to welcome view for initial disconnected state */}
      {!isConnected && !isReadyView && !isCallEndedView && !isFailedView && (
        <MotionView
          key="welcome-fallback"
          {...VIEW_MOTION_PROPS}
        >
          <WelcomeView
            startButtonText={appConfig.startButtonText}
            onStartCall={start}
            appConfig={appConfig}
          />
        </MotionView>
      )}
    </AnimatePresence>
  );
}