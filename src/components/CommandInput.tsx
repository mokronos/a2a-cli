import React from 'react';
import { Box, Text, Newline } from 'ink/build/index.js';
import TextInput from 'ink-text-input/build/index.js';

interface CommandInputProps {
  onCommand: (command: string) => void;
  placeholder?: string;
  connected: boolean;
  agentName?: string;
}

export function CommandInput({ onCommand, placeholder, connected, agentName }: CommandInputProps) {
  const [input, setInput] = React.useState('');

  const handleSubmit = (text: string) => {
    if (text.trim()) {
      onCommand(text.trim());
      setInput('');
    }
  };

  const prompt = connected 
    ? `[${agentName || 'agent'}] > `
    : '[not connected] > ';

  return React.createElement(
    Box,
    null,
    React.createElement(
      Text,
      { color: connected ? 'green' : 'red' },
      prompt
    ),
    React.createElement(
      TextInput,
      {
        value: input,
        onChange: setInput,
        onSubmit: handleSubmit,
        placeholder: placeholder || (connected ? 'Type your message or /help' : 'Use /connect <url> to connect')
      }
    )
  );
}

interface HelpScreenProps {
  onClose: () => void;
}

export function HelpScreen({ onClose }: HelpScreenProps) {
  return React.createElement(
    Box,
    { flexDirection: 'column' as const },
    React.createElement(
      Text,
      { color: 'cyan' as const, bold: true },
      'Available Commands:'
    ),
    React.createElement(Newline, null),
    React.createElement(
      Box,
      { flexDirection: 'column' as const, marginLeft: 2 },
      React.createElement(Text, null, '/connect <url>   - Connect to an A2A agent'),
      React.createElement(Text, null, '/disconnect       - Disconnect from the current agent'),
      React.createElement(Text, null, '/status           - Show current connection status'),
      React.createElement(Text, null, '/card             - Display the current agent card'),
      React.createElement(Text, null, '/reset, /new      - Reset conversation (new context)'),
      React.createElement(Text, null, '/help, /?         - Show this help message'),
      React.createElement(Text, null, '/quit, /exit      - Exit the CLI')
    ),
    React.createElement(Newline, null),
    React.createElement(Text, { color: 'gray' as const }, 'Tip: Use Tab for command autocompletion'),
    React.createElement(Newline, null),
    React.createElement(Text, null, 'Press any key to close...')
  );
}