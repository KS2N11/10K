"""
Structured logging utilities with trace event support.
"""
import json
import logging
import sys
from datetime import datetime
from typing import Any, Dict, Optional
from pathlib import Path


class JSONFormatter(logging.Formatter):
    """Custom formatter that outputs logs as JSON."""
    
    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        
        if hasattr(record, "extra"):
            log_data.update(record.extra)
        
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        return json.dumps(log_data)


def setup_logger(name: str, level: str = "INFO", log_format: str = "json") -> logging.Logger:
    """
    Set up a logger with the specified configuration.
    
    Args:
        name: Logger name
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_format: Format type ("json" or "text")
    
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper()))
    
    # Remove existing handlers
    logger.handlers.clear()
    
    # Console handler
    handler = logging.StreamHandler(sys.stdout)
    
    if log_format.lower() == "json":
        handler.setFormatter(JSONFormatter())
    else:
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        handler.setFormatter(formatter)
    
    logger.addHandler(handler)
    logger.propagate = False
    
    return logger


# Alias for backwards compatibility
get_logger = setup_logger


class TraceEvent:
    """Structured trace event for agent actions."""
    
    def __init__(
        self,
        agent: str,
        action: str,
        summary: str,
        artifacts: Optional[Dict[str, Any]] = None
    ):
        self.at = datetime.utcnow().isoformat() + "Z"
        self.agent = agent
        self.action = action
        self.summary = summary
        self.artifacts = artifacts or {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert trace event to dictionary."""
        return {
            "at": self.at,
            "agent": self.agent,
            "action": self.action,
            "summary": self.summary,
            "artifacts": self.artifacts
        }
    
    def __repr__(self) -> str:
        return f"TraceEvent(agent={self.agent}, action={self.action}, at={self.at})"


def log_trace_event(
    logger: logging.Logger,
    agent: str,
    action: str,
    summary: str,
    artifacts: Optional[Dict[str, Any]] = None
) -> TraceEvent:
    """
    Create and log a trace event.
    
    Args:
        logger: Logger instance
        agent: Name of the agent/component
        action: Action being performed
        summary: Human-readable summary
        artifacts: Optional additional data
    
    Returns:
        TraceEvent instance
    """
    event = TraceEvent(agent, action, summary, artifacts)
    logger.info(
        f"[TRACE] {agent}.{action}: {summary}",
        extra={"trace_event": event.to_dict()}
    )
    return event
