"""Constants for agent trace."""

# Semantic convention attributes for agent traces
ATTR_CONTRIBUTOR_TYPE = "agent_trace.contributor.type"
ATTR_MODEL_ID = "agent_trace.contributor.model_id"
ATTR_EVENT_TYPE = "agent_trace.event.type"
ATTR_FILE_PATH = "agent_trace.file.path"
ATTR_RANGE_START = "agent_trace.range.start_line"
ATTR_RANGE_END = "agent_trace.range.end_line"
ATTR_CONTENT_HASH = "agent_trace.range.content_hash"
ATTR_TOOL_NAME = "agent_trace.tool.name"
ATTR_SESSION_ID = "agent_trace.session.id"
ATTR_GIT_REVISION = "agent_trace.vcs.revision"
ATTR_TRANSCRIPT_URL = "agent_trace.conversation.url"

# Default trace file path
TRACE_FILE = ".agent-trace/traces.jsonl"

# Environment variable names
ENV_OTLP_ENDPOINT = "AGENT_TRACE_OTLP_ENDPOINT"
ENV_AZURE_CONNECTION_STRING = "APPLICATIONINSIGHTS_CONNECTION_STRING"
ENV_FILE_EXPORT = "AGENT_TRACE_FILE_EXPORT"
ENV_CONSOLE_EXPORT = "AGENT_TRACE_CONSOLE_EXPORT"
