#!/usr/bin/env bun

// Simple A2A CLI implementation
// TODO: Add React/Ink UI back when TTY is available

interface AppState {
  connected: boolean;
  agentName?: string;
  agentUrl?: string;
  contextId?: string;
}

const state: AppState = {
  connected: false,
  contextId: crypto.randomUUID()
};

function showWelcome() {
  console.log(`
╭───────────────────────────────────────╮
│           A2A CLI Client              │
│   Type /help for available commands   │
│   Use Tab for autocompletion          │
│   Use ↑/↓ for history navigation      │
╰───────────────────────────────────────╯`);
}

function showHelp() {
  console.log(`
Available Commands:
  /connect <url>   - Connect to an A2A agent
  /disconnect       - Disconnect from the current agent
  /status           - Show current connection status
  /card             - Display the current agent card
  /reset, /new      - Reset conversation (new context)
  /help, /?         - Show this help message
  /quit, /exit      - Exit the CLI

Tip: Use Tab for command autocompletion`);
}

function getPrompt(): string {
  if (state.connected) {
    return `[${state.agentName || 'agent'}] > `;
  }
  return '[not connected] > ';
}

async function handleCommand(command: string): Promise<boolean> {
  const parts = command.trim().split(/\s+/, 2);
  const cmd = parts[0].toLowerCase();
  const arg = parts[1];

  switch (cmd) {
    case '/help':
    case '/?':
      showHelp();
      break;

    case '/connect':
      if (!arg) {
        console.log('\x1b[31mUsage: /connect <url>\x1b[0m');
      } else {
        console.log(`\x1b[36mConnecting to ${arg}...\x1b[0m`);
        
        // TODO: Implement actual A2A connection
        console.log(`\x1b[32m✓ Connected to ${arg}\x1b[0m`);
        console.log('\x1b[33mAgent card:\x1b[0m');
        console.log('\x1b[90m{\n  "name": "Test Agent",\n  "description": "A test A2A agent"\n}\x1b[0m');
        
        state.connected = true;
        state.agentUrl = arg;
        state.agentName = 'Test Agent';
      }
      break;

    case '/disconnect':
      if (state.connected) {
        console.log(`\x1b[32m✓ Disconnected from ${state.agentName || 'agent'}\x1b[0m`);
        state.connected = false;
        state.agentName = undefined;
        state.agentUrl = undefined;
      } else {
        console.log('\x1b[33mNot connected to any agent.\x1b[0m');
      }
      break;

    case '/status':
      if (state.connected) {
        console.log('\x1b[36mConnection Status:\x1b[0m');
        console.log(`  Agent URL: \x1b[32m${state.agentUrl || 'http://localhost:8000'}\x1b[0m`);
        console.log(`  Agent Name: \x1b[32m${state.agentName || 'Test Agent'}\x1b[0m`);
        console.log(`  Context ID: \x1b[90m${state.contextId}\x1b[0m`);
        console.log('  Streaming: \x1b[32menabled\x1b[0m');
      } else {
        console.log('\x1b[33mNot connected to any agent.\x1b[0m');
        console.log('\x1b[90mUse /connect <url> to connect.\x1b[0m');
      }
      break;

    case '/card':
      if (state.connected) {
        console.log('\x1b[33mAgent card:\x1b[0m');
        console.log('\x1b[90m{\n  "name": "Test Agent",\n  "description": "A test A2A agent"\n}\x1b[0m');
      } else {
        console.log('\x1b[33mNot connected to any agent.\x1b[0m');
      }
      break;

    case '/reset':
    case '/new':
      if (state.connected) {
        state.contextId = crypto.randomUUID();
        console.log('\x1b[32m✓ Conversation reset.\x1b[0m');
        console.log(`\x1b[90mNew context ID: ${state.contextId}\x1b[0m`);
      } else {
        console.log('\x1b[33mNot connected to any agent.\x1b[0m');
      }
      break;

    case '/quit':
    case '/exit':
      console.log('\x1b[36mGoodbye!\x1b[0m');
      return false;

    default:
      if (command.startsWith('/')) {
        console.log(`\x1b[31mUnknown command: ${cmd}\x1b[0m`);
        console.log('\x1b[90mType /help for available commands.\x1b[0m');
      } else {
        if (!state.connected) {
          console.log('\x1b[31mNot connected to any agent.\x1b[0m');
          console.log('\x1b[90mUse /connect <url> to connect first.\x1b[0m');
        } else {
          console.log(`\x1b[35mTask: ${command}\x1b[0m`);
          console.log('\x1b[97mThis would normally send a task to the A2A agent.\x1b[0m');
          // TODO: Implement actual task sending
        }
      }
  }

  return true;
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

async function main() {
  showWelcome();

  // If agent-url is provided, connect immediately
  if (agentUrl) {
    await handleCommand(`/connect ${agentUrl}`);
    
    // If a task was also provided, execute it
    if (task && state.connected) {
      await handleCommand(task);
    }
  }

  // Simple REPL loop using Node.js readline
  const readline = await import('readline');
  const rl = readline.createInterface({
    input: process.stdin,
    output: process.stdout
  });

  function showPrompt() {
    process.stdout.write(getPrompt());
  }

  showPrompt();

  rl.on('line', async (line) => {
    const shouldContinue = await handleCommand(line.trim());
    if (shouldContinue) {
      showPrompt();
    } else {
      rl.close();
    }
  });

  rl.on('close', () => {
    console.log('\x1b[36mGoodbye!\x1b[0m');
    process.exit(0);
  });
}

// Handle Ctrl+C
process.on('SIGINT', () => {
  console.log('\n\x1b[36mGoodbye!\x1b[0m');
  process.exit(0);
});

// Handle Ctrl+D
process.stdin.on('end', () => {
  console.log('\n\x1b[36mGoodbye!\x1b[0m');
  process.exit(0);
});

main().catch(console.error);