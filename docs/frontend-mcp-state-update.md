# Frontend: MCP State Change WebSocket Handler

## Overview

The backend now broadcasts a WebSocket event whenever an MCP server's connection state changes (connected/disconnected). The frontend needs to handle this event to automatically refresh the MCP server list in the UI.

## WebSocket Command

A new WebSocket command `mcp_state_changed` is sent when:

- An MCP server successfully connects
- An MCP server disconnects
- An MCP server connection fails

### Command Structure

```typescript
interface McpStateChangedCommand {
	command: 'mcp_state_changed';
	wingman_name: string; // The wingman whose MCP state changed
}
```

## Implementation Requirements

### 1. Add WebSocket Handler

In the WebSocket message handler (where other commands like `log`, `toast`, etc. are handled), add a case for `mcp_state_changed`:

```typescript
case "mcp_state_changed":
  // Refresh MCP list if currently viewing this wingman's config
  if (currentWingmanName === message.wingman_name) {
    await refreshMcpServers();
  }
  break;
```

### 2. Trigger MCP List Refresh

When the `mcp_state_changed` event is received:

1. Check if the user is currently viewing the wingman config page for the affected wingman
2. If yes, call the `/wingman-mcps` endpoint to get the updated MCP server states
3. Update the UI to reflect the new connection states (green = connected, yellow = enabled but not connected, etc.)

### 3. API Endpoint Reference

```
GET /wingman-mcps?config_name={configName}&wingman_name={wingmanName}
```

Returns: `McpServerState[]`

```typescript
interface McpServerState {
	config: McpServerConfig;
	is_enabled: boolean;
	is_connected: boolean;
	tools: McpToolInfo[] | null;
	error: string | null;
}
```

## Expected Behavior

| Scenario                  | Before                               | After                                        |
| ------------------------- | ------------------------------------ | -------------------------------------------- |
| User opens wingman config | MCP shows yellow (not connected yet) | MCP automatically turns green when connected |
| User enables disabled MCP | MCP shows yellow                     | MCP automatically turns green when connected |
| MCP server disconnects    | MCP shows green                      | MCP automatically turns yellow/red           |

## Notes

- The backend already sends the event - no backend changes needed
- The 0.5s delay in the `/wingman-mcps` endpoint helps but doesn't guarantee connection is complete
- The WebSocket event provides real-time updates for a better UX
- Only refresh if the user is viewing the affected wingman's config (to avoid unnecessary API calls)
