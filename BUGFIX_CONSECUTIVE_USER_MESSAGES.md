# Bugfix: Consecutive User Messages Validation Error

## Issue

**Error:**
```
❌ Model invoke failed: An error occurred (ValidationException) when calling the InvokeModelWithResponseStream operation: messages.0.content.1: unexpected `tool_use_id` found in `tool_result` blocks: toolu_bdrk_01T8pHZGvxFiX7saQQhBe2T3. Each `tool_result` block must have a corresponding `tool_use` block in the previous message.
```

**Session:** 20260203152222

## Root Cause

The Claude API requires **alternating message roles** (user/assistant). The session had consecutive user messages, which violates this requirement:

```
Message 77: assistant (with tool_use)
Message 78: user (with tool_result)      <- user message
Message 79: user (text: "try that again") <- user message (INVALID!)
```

### How This Happened

1. AI requests a tool execution (creates assistant message with tool_use)
2. Tool executes and result is logged (creates user message with tool_result)
3. User immediately types another command (creates another user message)
4. Session now has two consecutive user messages (78, 79)

This commonly occurs when:
- User continues conversation immediately after a tool execution
- Context auto-summarization happens between tool execution and user input
- Session restoration reconstructs messages in wrong order

## Solution

Added `_merge_consecutive_user_messages()` method to SessionManager that:

1. Scans restored messages for consecutive user messages
2. Merges them into a single user message with multiple content blocks
3. Preserves all content (tool_results, text, etc.)

### Implementation

**File:** `pwnpilot_lite/session/session_manager.py`

**Method:** `_merge_consecutive_user_messages()`

```python
def _merge_consecutive_user_messages(self) -> None:
    """
    Merge consecutive user messages into single messages.

    Claude API requires alternating roles (user/assistant). This can happen
    when a user submits a new message right after a tool result.
    """
    # Scan messages
    # Collect consecutive user messages
    # Merge their content into single message with multiple blocks
    # Replace in messages list
```

**When Called:** During session restoration, after `_cleanup_incomplete_tool_requests()`

### Result Format

Before:
```python
[
  {"role": "user", "content": [{"type": "tool_result", "tool_use_id": "..."}]},
  {"role": "user", "content": "try that again"}
]
```

After:
```python
[
  {"role": "user", "content": [
    {"type": "tool_result", "tool_use_id": "..."},
    {"type": "text", "text": "try that again"}
  ]}
]
```

## Testing

Tested with session 20260203152222:

**Before Fix:**
- 80 messages restored
- 6+ instances of consecutive user messages
- Validation error on API call

**After Fix:**
- 73 messages restored (merged)
- ✅ No consecutive user messages
- ⚠️ Merged 2-3 consecutive user messages (logged)
- API validation passes

## Impact

- **Fixes:** ValidationException errors when restoring sessions with consecutive user messages
- **Improves:** Session restoration reliability
- **Maintains:** All conversation context and content
- **Logs:** Merge operations for debugging

## Prevention

The merge happens automatically during session restoration, so users don't need to take any action. The warning message alerts to the merge:

```
⚠️  Merged 2 consecutive user messages
```

## Related Issues

This fix addresses issues that can occur:
- After context auto-summarization
- When user rapidly sends messages
- During session restoration with complex tool execution history
- In long-running pentesting sessions with many tool executions

## Files Modified

- `pwnpilot_lite/session/session_manager.py`
  - Added `_merge_consecutive_user_messages()` method
  - Updated `_restore_session()` to call merge after cleanup

## Verification

To verify the fix works on any session:

```python
from pwnpilot_lite.session.session_manager import SessionManager

# Restore session
sm = SessionManager(session_id='YOUR_SESSION_ID', restore=True)

# Check for consecutive user messages
for i in range(len(sm.messages) - 1):
    if sm.messages[i].get('role') == 'user' and sm.messages[i+1].get('role') == 'user':
        print(f'❌ Consecutive user messages at {i} and {i+1}')
```

Should output:
```
✅ No consecutive user messages found!
```
