'use client';

import { useState } from 'react';
import { useDataChannel } from '@livekit/components-react';

/**
 * Listens for agent-handoff status messages published by the backend on the
 * "agent-status" data channel topic, and shows a transient "Switching to X…"
 * banner while a handoff is in progress.
 *
 * Backend publishes two messages per handoff:
 *   { type: "agent_handoff", status: "switching", to: "Arun" }  -> when the handoff starts
 *   { type: "agent_handoff", status: "complete",  to: "Arun" }  -> when the new agent takes over
 *
 * Usage: render this once inside your AgentSessionProvider tree, e.g.
 *   <AgentSessionProvider session={agentSession}>
 *     <AgentSwitchBanner />
 *     <AgentControlBar />
 *     ...
 *   </AgentSessionProvider>
 */

type HandoffStatus = {
  switching: boolean;
  to?: string;
};

type AgentHandoffMessage = {
  type: 'agent_handoff';
  status: 'switching' | 'complete';
  to: string;
};

export function AgentSwitchBanner() {
  const [status, setStatus] = useState<HandoffStatus>({ switching: false });

  useDataChannel('agent-status', (msg) => {
    let decoded: AgentHandoffMessage;
    try {
      decoded = JSON.parse(new TextDecoder().decode(msg.payload));
    } catch {
      return;
    }

    if (decoded.type !== 'agent_handoff') return;

    if (decoded.status === 'switching') {
      setStatus({ switching: true, to: decoded.to });
    } else if (decoded.status === 'complete') {
      // Keep the banner up briefly so it doesn't just flash on fast handoffs
      setTimeout(() => setStatus({ switching: false }), 600);
    }
  });

  if (!status.switching) return null;

  return (
    <div
      role="status"
      aria-live="polite"
      className="fixed top-4 left-1/2 z-50 -translate-x-1/2 animate-pulse rounded-full bg-black/80 px-4 py-2 text-sm text-white shadow-lg"
    >
      Switching to {status.to ?? 'specialist'}…
    </div>
  );
}