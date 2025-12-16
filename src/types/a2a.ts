interface AgentCard {
  name: string;
  description?: string;
  capabilities: {
    streaming: boolean;
  };
  [key: string]: any;
}

interface Part {
  text?: string;
  data?: string;
  file?: {
    name: string;
    url: string;
  };
}

interface Message {
  role: 'user' | 'assistant' | 'system';
  parts: Part[];
  messageId: string;
  contextId: string;
  [key: string]: any;
}

interface TaskArtifact {
  name: string;
  parts: Part[];
  [key: string]: any;
}

interface TaskStatus {
  state: 'queued' | 'running' | 'completed' | 'failed';
  message?: string;
  [key: string]: any;
}

interface TaskArtifactUpdateEvent {
  artifact: TaskArtifact;
  [key: string]: any;
}

interface TaskStatusUpdateEvent {
  status: TaskStatus;
  [key: string]: any;
}

interface A2AEvent {
  type?: string;
  message?: Message;
  task?: TaskStatus;
  update?: TaskArtifactUpdateEvent | TaskStatusUpdateEvent;
}

interface A2ASessionState {
  connected: boolean;
  agentUrl?: string;
  agentCard?: AgentCard;
  contextId?: string;
  streaming?: boolean;
}

export type {
  AgentCard,
  Part,
  Message,
  TaskArtifact,
  TaskStatus,
  TaskArtifactUpdateEvent,
  TaskStatusUpdateEvent,
  A2AEvent,
  A2ASessionState
};