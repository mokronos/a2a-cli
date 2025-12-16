import { useEffect, useRef, useState } from 'react';
import got from 'got';
import {
  A2AEvent,
  AgentCard,
  Message,
  TaskArtifact,
  TaskStatus,
  Part,
} from '../types/a2a';

export interface A2ASession {
  agentUrl: string;
  agentCard: AgentCard | null;
  isConnected: boolean;
  isLoading: boolean;
  error: string | null;
  events: A2AEvent[];
  connect: (agentUrl: string) => Promise<void>;
  disconnect: () => void;
  sendTask: (task: string) => Promise<void>;
  reset: () => void;
}

export function useA2ASession(): A2ASession {
  const [agentUrl, setAgentUrl] = useState<string>('');
  const [agentCard, setAgentCard] = useState<AgentCard | null>(null);
  const [isConnected, setIsConnected] = useState<boolean>(false);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [events, setEvents] = useState<A2AEvent[]>([]);
  const abortControllerRef = useRef<AbortController | null>(null);

  const connect = async (url: string): Promise<void> => {
    try {
      setIsLoading(true);
      setError(null);
      
      // Fetch agent card
      const cardResponse = await got.get(`${url}/card`, {
        responseType: 'json',
        timeout: 5000,
      });
      
      setAgentCard(cardResponse.body as unknown as AgentCard);
      setAgentUrl(url);
      setIsConnected(true);
    } catch (err) {
      setError(`Failed to connect to agent: ${err instanceof Error ? err.message : 'Unknown error'}`);
      setIsConnected(false);
    } finally {
      setIsLoading(false);
    }
  };

  const disconnect = (): void => {
    // Abort any ongoing requests
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
    
    setIsConnected(false);
    setAgentCard(null);
    setAgentUrl('');
    setEvents([]);
    setError(null);
  };

  const sendTask = async (task: string): Promise<void> => {
    if (!isConnected || !agentUrl) {
      setError('Not connected to an agent');
      return;
    }

    try {
      setIsLoading(true);
      setError(null);
      
      // Abort any ongoing requests
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
      abortControllerRef.current = new AbortController();

      // Clear previous events
      setEvents([]);

      // Send task request with streaming
      const response = await got.post(`${agentUrl}/task`, {
        json: { messages: [{ role: 'user', content: task, timestamp: Date.now() }] },
        responseType: 'text',
        timeout: 30000,
        headers: {
          'Accept': 'text/event-stream',
          'Cache-Control': 'no-cache',
        },
        signal: abortControllerRef.current.signal,
      });

      // Parse SSE response
      const lines = response.body.split('\n');
      let eventType = '';
      let eventData = '';

      for (const line of lines) {
        if (line.startsWith('event: ')) {
          eventType = line.substring(7);
        } else if (line.startsWith('data: ')) {
          eventData += line.substring(6) + '\n';
        } else if (line === '' && eventData) {
          // End of event data
          if (eventType) {
            const parsedData = JSON.parse(eventData.trim());
            const event: A2AEvent = {
              type: eventType,
              data: parsedData,
              timestamp: Date.now(),
            } as A2AEvent;
            
            processEvent(event);
          }
          eventType = '';
          eventData = '';
        }
      }

      // Process any remaining event
      if (eventType && eventData) {
        const parsedData = JSON.parse(eventData.trim());
        const event: A2AEvent = {
          type: eventType,
          data: parsedData,
          timestamp: Date.now(),
        } as A2AEvent;
        
        processEvent(event);
      }

    } catch (err) {
      if (err instanceof Error && err.name === 'AbortError') {
        setError('Task request was cancelled');
      } else {
        setError(`Failed to send task: ${err instanceof Error ? err.message : 'Unknown error'}`);
      }
    } finally {
      setIsLoading(false);
      // Clear abort controller
      abortControllerRef.current = null;
    }
  };

  const processEvent = (event: A2AEvent): void => {
    setEvents(prev => [...prev, event]);
  };

  const reset = (): void => {
    setEvents([]);
    setError(null);
  };

  useEffect(() => {
    // Cleanup on unmount
    return () => {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
  }, []);

  return {
    agentUrl,
    agentCard,
    isConnected,
    isLoading,
    error,
    events,
    connect,
    disconnect,
    sendTask,
    reset,
  };
}