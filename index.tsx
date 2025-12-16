#!/usr/bin/env bun

import React, { useEffect, useMemo, useRef, useState } from 'react';
import { render, Box, Text, useApp, useInput } from 'ink';
import { ClientFactory } from '@a2a-js/sdk/client';
import { Message, MessageSendParams, AgentCard } from '@a2a-js/sdk';
import { v4 as uuidv4 } from 'uuid';

// Types
 type A2AClient = Awaited<ReturnType<ClientFactory['createFromUrl']>>;
 type LogEntry = { text: string; color?: string };

 const SLASH_COMMANDS = [
   '/connect',
   '/disconnect',
   '/status',
   '/card',
   '/reset',
   '/new',
   '/help',
   '/?',
   '/quit',
   '/exit'
 ];

 const truncateTaskId = (taskId: string, maxLength = 8) =>
   taskId.length <= maxLength ? taskId : `${taskId.substring(0, maxLength)}...`;

 type ConnectionState = {
   connected: boolean;
   agentName?: string;
   agentUrl?: string;
   agentCard?: AgentCard;
   client?: A2AClient;
   contextId: string;
 };

 const Welcome = () => (
   <Box flexDirection="column">
     <Text>╭───────────────────────────────────────╮</Text>
     <Text>│           A2A CLI Client              │</Text>
     <Text>│   Type /help for available commands   │</Text>
     <Text>│   Use Tab for autocompletion          │</Text>
     <Text>│   Use ↑/↓ for history navigation      │</Text>
     <Text>╰───────────────────────────────────────╯</Text>
   </Box>
 );

 function useSuggestions(input: string) {
   return useMemo(() => {
     if (!input.startsWith('/')) return { items: [] as string[], selected: 0 };
     if (input.includes(' ')) return { items: [] as string[], selected: 0 };
     const matches = SLASH_COMMANDS.filter(c => c.startsWith(input));
     return { items: matches.length ? matches : SLASH_COMMANDS, selected: 0 };
   }, [input]);
 }

 function useHistory() {
   const [list, setList] = useState<string[]>([]);
   const [index, setIndex] = useState(-1);
   const push = (item: string) => {
     if (!item.trim()) return;
     setList(prev => [...prev, item]);
     setIndex(-1);
   };
   const move = (delta: number, current: string) => {
     if (!list.length) return current;
     let next = index === -1 ? list.length : index;
     next += delta;
     if (next < 0) next = 0;
     if (next > list.length - 1) {
       setIndex(-1);
       return '';
     }
     setIndex(next);
     return list[next] ?? '';
   };
   return { push, move };
 }

 async function connectToAgent(url: string): Promise<{ agentCard: AgentCard; client: A2AClient; normalizedUrl: string }> {
   let normalizedUrl = url;
   if (!normalizedUrl.startsWith('http://') && !normalizedUrl.startsWith('https://')) {
     normalizedUrl = 'http://' + normalizedUrl;
   }
   const factory = new ClientFactory();
   const client = await factory.createFromUrl(normalizedUrl);
   const cardRes = await fetch(`${normalizedUrl}/.well-known/agent-card.json`);
   if (!cardRes.ok) throw new Error(`Failed to fetch agent card: ${cardRes.status} ${cardRes.statusText}`);
   const agentCard = (await cardRes.json()) as AgentCard;
   return { agentCard, client, normalizedUrl };
 }

 const App: React.FC = () => {
   const { exit } = useApp();
   const [connection, setConnection] = useState<ConnectionState>({
     connected: false,
     contextId: crypto.randomUUID()
   });
   const [input, setInput] = useState('');
   const [logs, setLogs] = useState<LogEntry[]>([]);
   const [busy, setBusy] = useState(false);
   const history = useHistory();
   const suggestions = useSuggestions(input);
   const [selectedSuggestion, setSelectedSuggestion] = useState(0);
   const streamingBuffer = useRef('');

   useEffect(() => {
     if (selectedSuggestion >= suggestions.items.length) setSelectedSuggestion(0);
     if (suggestions.items.length === 0) setSelectedSuggestion(0);
   }, [suggestions.items.length, selectedSuggestion]);

   const log = (text: string, color?: string) => setLogs(prev => [...prev, { text, color }].slice(-500));

   const prompt = connection.connected ? `[${connection.agentName || 'agent'}] > ` : '[not connected] > ';

   const handleTaskSend = async (taskText: string) => {
     if (!connection.client) return;
     setBusy(true);
     streamingBuffer.current = '';
     const sendParams: MessageSendParams = {
       message: {
         messageId: uuidv4(),
         role: 'user',
         parts: [{ kind: 'text', text: taskText }],
         kind: 'message'
       }
     };
     const supportsStreaming = connection.agentCard?.capabilities?.streaming ?? false;
     try {
       if (supportsStreaming) {
         const stream = connection.client.sendMessageStream(sendParams);
         for await (const event of stream) {
           if (event.kind === 'task') {
             log(`[${truncateTaskId(event.id)}] Task created. Status: ${event.status?.state || 'unknown'}`, 'yellow');
           } else if (event.kind === 'status-update') {
             log(`[${truncateTaskId(event.taskId)}] Status: ${event.status?.state || 'unknown'}`, 'yellow');
             if (event.status?.state === 'completed') log('✓ Task completed', 'green');
             if (event.status?.state === 'failed') log(`✗ Task failed: ${event.status?.message || 'Unknown error'}`, 'red');
           } else if (event.kind === 'artifact-update') {
             const artifactName = event.artifact?.name || event.artifact?.artifactId || '';
             if (artifactName === 'output_start') {
               streamingBuffer.current = '';
             } else if (artifactName === 'output_delta') {
               for (const part of event.artifact?.parts || []) {
                 if (part.kind === 'text') streamingBuffer.current += part.text;
               }
             } else if (artifactName === 'output_end' || artifactName === 'full_output') {
               for (const part of event.artifact?.parts || []) {
                 if (part.kind === 'text') streamingBuffer.current += part.text;
               }
               if (streamingBuffer.current) {
                 log(streamingBuffer.current, 'white');
                 streamingBuffer.current = '';
               }
             } else {
               log(`Artifact: ${artifactName}`, 'yellow');
               for (const part of event.artifact?.parts || []) {
                 if (part.kind === 'text') log(part.text, 'white');
               }
             }
           } else if (event.kind === 'message') {
             for (const part of (event as Message).parts) {
               if (part.kind === 'text') log(part.text, 'white');
             }
           }
         }
       } else {
         const result = await connection.client.sendMessage(sendParams);
         if (result.kind === 'message') {
           (result as Message).parts.forEach(p => {
             if (p.kind === 'text') log(p.text, 'white');
           });
         } else if (result.kind === 'task') {
           const task = result as any;
           log(`Task [${truncateTaskId(task.id)}] status: ${task.status?.state || 'unknown'}`, 'yellow');
           for (const artifact of task.artifacts || []) {
             log(`Artifact: ${artifact.name || artifact.artifactId}`, 'yellow');
             for (const part of artifact.parts || []) {
               if (part.kind === 'text') log(part.text, 'white');
             }
           }
         }
       }
     } catch (e: any) {
       log(`Error sending task: ${e?.message || 'Unknown error'}`, 'red');
     } finally {
       setBusy(false);
     }
   };

   const handleCommand = async (cmd: string) => {
     const trimmed = cmd.trim();
     if (!trimmed) return;
     history.push(trimmed);
     setInput('');
     setSelectedSuggestion(0);

     const [command, arg] = trimmed.split(/\s+/, 2);
     switch (command.toLowerCase()) {
       case '/help':
       case '/?':
         log(
           'Available Commands:\n  /connect <url>\n  /disconnect\n  /status\n  /card\n  /reset, /new\n  /help, /?\n  /quit, /exit',
           'cyan'
         );
         return;
       case '/connect':
         if (!arg) {
           log('Usage: /connect <url>', 'red');
           return;
         }
         if (busy) {
           log('Already processing. Please wait.', 'yellow');
           return;
         }
         setBusy(true);
         log(`Connecting to ${arg}...`, 'cyan');
         try {
           const { agentCard, client, normalizedUrl } = await connectToAgent(arg);
           setConnection(prev => ({
             ...prev,
             connected: true,
             agentUrl: normalizedUrl,
             agentName: agentCard.name || 'Unknown Agent',
             agentCard,
             client
           }));
           log(`✓ Connected to ${normalizedUrl}`, 'green');
         } catch (e: any) {
           log(`Failed to connect: ${e?.message || 'Unknown error'}`, 'red');
         } finally {
           setBusy(false);
         }
         return;
       case '/disconnect':
         setConnection(prev => ({
           connected: false,
           contextId: prev.contextId,
           agentCard: undefined,
           agentName: undefined,
           agentUrl: undefined,
           client: undefined
         }));
         log('✓ Disconnected', 'green');
         return;
       case '/status':
         if (connection.connected) {
           log(
             `Connection Status:\n  Agent URL: ${connection.agentUrl}\n  Agent Name: ${connection.agentName}\n  Context ID: ${connection.contextId}\n  Streaming: enabled`,
             'cyan'
           );
         } else {
           log('Not connected. Use /connect <url>.', 'yellow');
         }
         return;
       case '/card':
         if (connection.agentCard) {
           log(JSON.stringify(connection.agentCard, null, 2), 'gray');
         } else {
           log('Not connected to any agent.', 'yellow');
         }
         return;
       case '/reset':
       case '/new':
         if (!connection.connected) {
           log('Not connected to any agent.', 'yellow');
           return;
         }
         const newContext = crypto.randomUUID();
         setConnection(prev => ({ ...prev, contextId: newContext }));
         log(`✓ Conversation reset. New context: ${newContext}`, 'green');
         return;
       case '/quit':
       case '/exit':
         log('Goodbye!', 'cyan');
         exit();
         return;
       default:
         if (!connection.connected || !connection.client) {
           log('Not connected. Use /connect <url> first.', 'red');
           return;
         }
         await handleTaskSend(trimmed);
     }
   };

   useInput((inputChar, key) => {
     if (key.return) {
       handleCommand(input);
       return;
     }
     if (key.tab) {
       if (suggestions.items.length > 0) {
         const sel = suggestions.items[selectedSuggestion] || suggestions.items[0];
         setInput(sel.endsWith(' ') ? sel : `${sel} `);
       }
       return;
     }
     if (key.ctrl && key.name === 'c') {
       setInput('');
       setSelectedSuggestion(0);
       return;
     }
     if (key.upArrow || (key.ctrl && key.name === 'p')) {
       if (suggestions.items.length > 0 && input.startsWith('/')) {
         setSelectedSuggestion(prev =>
           suggestions.items.length === 0 ? 0 : (prev - 1 + suggestions.items.length) % suggestions.items.length
         );
       } else {
         const val = history.move(-1, input);
         setInput(val);
       }
       return;
     }
     if (key.downArrow || (key.ctrl && key.name === 'n')) {
       if (suggestions.items.length > 0 && input.startsWith('/')) {
         setSelectedSuggestion(prev =>
           suggestions.items.length === 0 ? 0 : (prev + 1) % suggestions.items.length
         );
       } else {
         const val = history.move(1, input);
         setInput(val);
       }
       return;
     }
     if (key.backspace || key.delete) {
       setInput(prev => prev.slice(0, -1));
       return;
     }
     if (!key.ctrl && !key.meta) {
       setInput(prev => prev + inputChar);
     }
   });

   return (
     <Box flexDirection="column">
       <Welcome />
       <Box borderStyle="round" padding={1} flexDirection="column">
         <Text color="gray">Output:</Text>
         {logs.map((l, idx) => (
           <Text key={idx} color={l.color as any}>{l.text}</Text>
         ))}
       </Box>
       <Box marginTop={1} flexDirection="column">
         <Box>
           <Text color={connection.connected ? 'green' : 'red'}>{prompt}</Text>
           <Text>{input || (busy ? '…' : '')}</Text>
         </Box>
         {input.startsWith('/') && suggestions.items.length > 0 && (
           <Box flexDirection="column" marginLeft={2} borderStyle="classic" padding={1}>
             <Text color="gray">Suggestions (Tab to accept, ↑/↓ or Ctrl-P/N to navigate):</Text>
             {suggestions.items.map((s, idx) => (
               <Text key={s} inverse={idx === selectedSuggestion}>{s}</Text>
             ))}
           </Box>
         )}
       </Box>
     </Box>
   );
 };

 render(<App />);
