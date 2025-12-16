#!/usr/bin/env bun

import React from 'react';
import { render, Box, Text, Newline } from 'ink';
import { CommandInput } from './components/CommandInput';

interface AppProps {
  agentUrl?: string;
  task?: string;
}

function App({ agentUrl, task }: AppProps) {
  const [output, setOutput] = React.useState<string[]>([]);
  const [connected, setConnected] = React.useState(false);
  const [agentName, setAgentName] = React.useState<string | undefined>(undefined);

  const addToOutput = (text: string, color?: string) => {
    setOutput(prev => [...prev, color ? `\x1b[${color}m${text}\x1b[0m` : text]);
  };

  const handleCommand = async (command: string) => {
    const parts = command.trim().split(/\s+/, 2);
    const cmd = parts[0].toLowerCase();
    const arg = parts[1];

    switch (cmd) {
      case '/help':
      case '/?':
        addToOutput(`
Available Commands:
  /connect <url>   - Connect to an A2A agent
  /disconnect       - Disconnect from the current agent
  /status           - Show current connection status
  /card             - Display the current agent card
  /reset, /new      - Reset conversation (new context)
  /help, /?         - Show this help message
  /quit, /exit      - Exit the CLI

Tip: Use Tab for command autocompletion
`, '36'); // cyan
        break;

      case '/connect':
        if (!arg) {
          addToOutput('Usage: /connect <url>', '31'); // red
        } else {
          addToOutput(`Connecting to ${arg}...`, '36'); // cyan
          addToOutput(`✓ Connected to ${arg}`, '32'); // green
          addToOutput('Agent card:', '33'); // yellow
          addToOutput(JSON.stringify({ name: 'Test Agent', description: 'A test A2A agent' }, null, 2), '90'); // bright black
          setConnected(true);
          setAgentName('Test Agent');
        }
        break;

      case '/disconnect':
        if (connected) {
          addToOutput(`✓ Disconnected from ${agentName || 'agent'}`, '32'); // green
          setConnected(false);
          setAgentName(undefined);
        } else {
          addToOutput('Not connected to any agent.', '33'); // yellow
        }
        break;

      case '/status':
        if (connected) {
          addToOutput('Connection Status:', '36'); // cyan
          addToOutput(`  Agent URL: ${agentUrl || 'http://localhost:8000'}`, '32'); // green
          addToOutput(`  Agent Name: ${agentName || 'Test Agent'}`, '32'); // green
          addToOutput(`  Context ID: ${crypto.randomUUID()}`, '90'); // bright black
          addToOutput('  Streaming: enabled', '32'); // green
        } else {
          addToOutput('Not connected to any agent.', '33'); // yellow
          addToOutput('Use /connect <url> to connect.', '90'); // bright black
        }
        break;

      case '/card':
        if (connected) {
          addToOutput('Agent card:', '33'); // yellow
          addToOutput(JSON.stringify({ name: 'Test Agent', description: 'A test A2A agent' }, null, 2), '90'); // bright black
        } else {
          addToOutput('Not connected to any agent.', '33'); // yellow
        }
        break;

      case '/reset':
      case '/new':
        if (connected) {
          const newContext = crypto.randomUUID();
          addToOutput('✓ Conversation reset.', '32'); // green
          addToOutput(`New context ID: ${newContext}`, '90'); // bright black
        } else {
          addToOutput('Not connected to any agent.', '33'); // yellow
        }
        break;

      case '/quit':
      case '/exit':
        process.exit(0);
        break;

      default:
        if (command.startsWith('/')) {
          addToOutput(`Unknown command: ${cmd}`, '31'); // red
          addToOutput('Type /help for available commands.', '90'); // bright black
        } else {
          if (!connected) {
            addToOutput('Not connected to any agent.', '31'); // red
            addToOutput('Use /connect <url> to connect first.', '90'); // bright black
          } else {
            addToOutput(`Task: ${command}`, '35'); // magenta
            addToOutput('This would normally send a task to the A2A agent.', '97'); // bright white
          }
        }
    }
  };

  return React.createElement(
    Box,
    { flexDirection: 'column' as const },
    React.createElement(
      Box,
      null,
      React.createElement(
        Text,
        { color: 'cyan' as const, bold: true },
        '╭───────────────────────────────────────╮\n│           A2A CLI Client              │\n│   Type /help for available commands   │\n│   Use Tab for autocompletion          │\n│   Use ↑/↓ for history navigation      │\n╰───────────────────────────────────────╯'
      )
    ),
    
    React.createElement(
      Box,
      { flexDirection: 'column' as const },
      output.map((line, index) => 
        React.createElement(Text, { key: index }, line)
      )
    ),

    React.createElement(Newline, null),
    
    React.createElement(
      CommandInput,
      {
        onCommand: handleCommand,
        connected,
        agentName
      }
    )
  );
}

// Parse command line arguments
const args = process.argv.slice(2);
let agentUrl: string | undefined = undefined;
let task: string | undefined = undefined;

for (let i = 0; i < args.length; i++) {
  if (args[i] === '--agent-url' && i + 1 < args.length) {
    agentUrl = args[i + 1];
    i++;
  } else if (args[i] === '--task' && i + 1 < args.length) {
    task = args[i + 1];
    i++;
  }
}

// Render the app
const { unmount } = render(
  React.createElement(App, { agentUrl, task })
);

// Handle Ctrl+C
process.on('SIGINT', () => {
  unmount();
  process.exit(0);
});

// Handle Ctrl+D
process.stdin.on('end', () => {
  unmount();
  process.exit(0);
});