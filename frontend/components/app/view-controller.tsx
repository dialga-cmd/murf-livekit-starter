'use client';

console.log('ViewController file loaded');

import { useTheme } from 'next-themes';
import { useCallback, useEffect, useState } from 'react';

console.log('ViewController component function called');
import { AnimatePresence, motion } from 'motion/react';
import { useSessionContext, useAgent } from '@livekit/components-react';
import type { AppConfig } from '@/app-config';
import type { AgentState } from '@livekit/components-react';
import { WelcomeView } from '@/components/app/welcome-view';
import { AgentConnectingView } from '@/components/app/agent-connecting-view';
import { AgentListeningView } from '@/components/app/agent-listening-view';
import { AgentSpeakingView } from '@/components/app/agent-speaking-view';
import { AgentCallEndedView } from '@/components/app/agent-call-ended-view';
import { AgentReadyView } from '@/components/app/agent-ready-view';

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
    ease: 'linear' as const,
  },
};

interface ViewControllerProps {
  appConfig: AppConfig;
}

export function ViewController({ appConfig }: ViewControllerProps) {
  console.log('ViewController render start');
  const { isConnected, start, end } = useSessionContext();
  const agent = useAgent();
  const { resolvedTheme } = useTheme();
  const [hasEverStartedCall, setHasEverStartedCall] = useState(false);

  // If agent is null, show a placeholder
  if (!agent) {
    console.log('ViewController: Agent is null, showing placeholder');
    return (
      <>
        <div className="text-center py-12">
          <p>Agent is null</p>
        </div>
      </>
    );
  }

  console.log('ViewController props:', { appConfig });
  console.log('ViewController hooks:', { isConnected, agent: !!agent });
  console.log('ViewController agent object:', agent);

  // Wrap start function to track when it's called
  const trackedStart = useCallback(async () => {
    setHasEverStartedCall(true);
    return start();
  }, [start]);

  // Determine which view to show based on agent state
  const isReadyView = !agent.isConnected && !hasEverStartedCall && agent.state === 'disconnected';
  const isConnectingView = agent.state === 'connecting' || agent.state === 'pre-connect-buffering';
  const isListeningView = agent.state === 'listening';
  const isSpeakingView = agent.state === 'speaking';
  // Call ended view only shows if we've actually started a call before
  const isCallEndedView = agent.state === 'disconnected' && agent.isFinished && hasEverStartedCall;
  const isFailedView = agent.state === 'failed';

  // Debug logging for agent
  useEffect(() => {
    console.log('ViewController agent useEffect triggered:', agent);
    console.log('ViewController isConnected (session) useEffect triggered:', isConnected);
  }, [agent, isConnected]);

  // Debug logging
  useEffect(() => {
    console.log('ViewController debug:', {
      agentState: agent.state,
      agentIsConnected: agent.isConnected,
      agentIsFinished: agent.isFinished,
      sessionIsConnected: isConnected,
      hasEverStartedCall,
      isReadyView,
      isConnectingView,
      isListeningView,
      isSpeakingView,
      isCallEndedView,
      isFailedView
    });
  }, [agent.state, agent.isConnected, agent.isFinished, isConnected, hasEverStartedCall]);

  return (
    <>
      <AnimatePresence mode="wait">
        {/* Ready view - show when agent is idle and not connected */}
        {isReadyView && (
          <MotionView
            key="ready"
            {...VIEW_MOTION_PROPS}
          >
            <AgentReadyView
              onStartCall={trackedStart}
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
              onStartCall={trackedStart}
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
                onClick={(e) => trackedStart()}
                className="mt-6 btn btn-primary"
              >
                Try Again
              </button>
            </div>
          </MotionView>
        )}
      </AnimatePresence>
      {isConnected && (
        <button
          onClick={end}
          className="fixed bottom-4 left-1/2 transform -translate-x-1/2 bg-destructive text-white px-4 py-2 rounded hover:bg-destructive/90 transition-colors z-50"
        >
          End Call
        </button>
      )}
    </>
  );
}