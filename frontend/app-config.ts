export interface AppConfig {
  pageTitle: string;
  pageDescription: string;
  companyName: string;

  supportsChatInput: boolean;
  supportsVideoInput: boolean;
  supportsScreenShare: boolean;
  isPreConnectBufferEnabled: boolean;

  logo: string;
  startButtonText: string;
  accent?: string;
  logoDark?: string;
  accentDark?: string;

  audioVisualizerType?: 'bar' | 'wave' | 'grid' | 'radial' | 'aura';
  audioVisualizerColor?: `#${string}`;
  audioVisualizerColorDark?: `#${string}`;
  audioVisualizerColorShift?: number;
  audioVisualizerBarCount?: number;
  audioVisualizerGridRowCount?: number;
  audioVisualizerGridColumnCount?: number;
  audioVisualizerRadialBarCount?: number;
  audioVisualizerRadialRadius?: number;
  audioVisualizerWaveLineWidth?: number;

  // agent dispatch configuration
  agentName?: string;

  // LiveKit Cloud Sandbox configuration
  sandboxId?: string;
}

export const APP_CONFIG_DEFAULTS: AppConfig = {
  companyName: 'Health Access Voice Agent',
  pageTitle: 'Health Access Voice Agent - Powered by Murf Falcon',
  pageDescription: 'Get healthcare information, find clinics, and prepare for appointments with your multilingual health assistant',

  supportsChatInput: true,
  supportsVideoInput: false,  // Keep it simple for health access - no video needed
  supportsScreenShare: false, // No screen sharing for health consultations
  isPreConnectBufferEnabled: true,

  logo: '/healthcare-logo.svg',  // We'll create this or use a default
  accent: '#10B981',           // Green color for healthcare/wellness
  logoDark: '/healthcare-logo-dark.svg',
  accentDark: '#34D399',
  startButtonText: 'Start Health Consultation',

  // Audio visualization - using bar style for clean, professional look
  audioVisualizerType: 'bar',
  audioVisualizerColor: '#10B981',
  audioVisualizerColorDark: '#34D399',
  audioVisualizerBarCount: 6,

  // agent dispatch configuration
  agentName: process.env.AGENT_NAME ?? undefined,

  // LiveKit Cloud Sandbox configuration
  sandboxId: undefined,
};
