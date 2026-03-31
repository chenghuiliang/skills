# Message bus implementations for multi-agent system
# All comments in this file are in English per project guidelines

import json
import os
import time
import glob
from abc import ABC, abstractmethod

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    redis = None
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set
from threading import Lock, Thread
import queue

from .message import Message, MessageType


class MessageBus(ABC):
    """Abstract base class for message bus implementations."""

    def __init__(self, namespace: str = "torch_npu_agents"):
        """Initialize message bus.

        Args:
            namespace: Namespace for isolating different bus instances.
        """
        self.namespace = namespace
        self.subscribers: Dict[str, List[Callable[[Message], None]]] = {}
        self.running = False
        self._lock = Lock()

    @abstractmethod
    def publish(self, message: Message) -> bool:
        """Publish a message to the bus.

        Args:
            message: Message to publish.

        Returns:
            True if published successfully.
        """
        pass

    @abstractmethod
    def subscribe(self, agent_id: str, callback: Callable[[Message], None]) -> bool:
        """Subscribe an agent to receive messages.

        Args:
            agent_id: Unique identifier for the agent.
            callback: Function to call when message is received.

        Returns:
            True if subscribed successfully.
        """
        pass

    @abstractmethod
    def unsubscribe(self, agent_id: str) -> bool:
        """Unsubscribe an agent.

        Args:
            agent_id: Agent identifier.

        Returns:
            True if unsubscribed successfully.
        """
        pass

    @abstractmethod
    def get_messages_for(self, agent_id: str, since: Optional[datetime] = None) -> List[Message]:
        """Get pending messages for an agent.

        Args:
            agent_id: Agent identifier.
            since: Only get messages since this time.

        Returns:
            List of messages.
        """
        pass

    def start(self):
        """Start the message bus."""
        self.running = True

    def stop(self):
        """Stop the message bus."""
        self.running = False

    def broadcast(self, sender: str, message_type: MessageType, payload: Dict[str, Any]) -> bool:
        """Broadcast a message to all agents.

        Args:
            sender: Sending agent ID.
            message_type: Type of message.
            payload: Message payload.

        Returns:
            True if broadcast successfully.
        """
        message = Message(
            sender=sender,
            recipient="",  # Empty = broadcast
            message_type=message_type,
            payload=payload,
        )
        return self.publish(message)


class FileMessageBus(MessageBus):
    """File-based message bus for single-machine multi-process communication.

    Uses a directory structure for message exchange.
    """

    def __init__(self, namespace: str = "torch_npu_agents", base_dir: str = ".agent_messages"):
        """Initialize file-based message bus.

        Args:
            namespace: Namespace for this bus instance.
            base_dir: Base directory for message files.
        """
        super().__init__(namespace)
        self.base_dir = Path(base_dir) / namespace
        self.inbox_dir = self.base_dir / "inbox"
        self.broadcast_dir = self.base_dir / "broadcast"
        self._ensure_dirs()
        self._poll_thread: Optional[Thread] = None

    def _ensure_dirs(self):
        """Create necessary directories."""
        self.inbox_dir.mkdir(parents=True, exist_ok=True)
        self.broadcast_dir.mkdir(parents=True, exist_ok=True)

    def _get_inbox_path(self, agent_id: str) -> Path:
        """Get inbox directory for an agent."""
        inbox = self.inbox_dir / agent_id
        inbox.mkdir(parents=True, exist_ok=True)
        return inbox

    def _message_file_name(self, message: Message) -> str:
        """Generate file name for a message."""
        timestamp = message.timestamp.strftime("%Y%m%d_%H%M%S_%f")
        return f"{timestamp}_{message.message_id}.json"

    def publish(self, message: Message) -> bool:
        """Publish message to file system."""
        try:
            if message.recipient:
                # Direct message
                inbox = self._get_inbox_path(message.recipient)
                file_path = inbox / self._message_file_name(message)
            else:
                # Broadcast
                file_path = self.broadcast_dir / self._message_file_name(message)

            with open(file_path, 'w') as f:
                f.write(message.to_json())
            return True
        except Exception as e:
            print(f"Failed to publish message: {e}")
            return False

    def subscribe(self, agent_id: str, callback: Callable[[Message], None]) -> bool:
        """Subscribe agent to receive messages."""
        with self._lock:
            if agent_id not in self.subscribers:
                self.subscribers[agent_id] = []
            self.subscribers[agent_id].append(callback)
        return True

    def unsubscribe(self, agent_id: str) -> bool:
        """Unsubscribe agent."""
        with self._lock:
            if agent_id in self.subscribers:
                del self.subscribers[agent_id]
        return True

    def get_messages_for(self, agent_id: str, since: Optional[datetime] = None) -> List[Message]:
        """Get pending messages for agent."""
        messages = []

        # Get direct messages
        inbox = self._get_inbox_path(agent_id)
        for file_path in inbox.glob("*.json"):
            try:
                with open(file_path, 'r') as f:
                    message = Message.from_json(f.read())
                if since is None or message.timestamp > since:
                    messages.append(message)
                # Remove processed message
                file_path.unlink()
            except Exception:
                continue

        # Get broadcasts
        for file_path in self.broadcast_dir.glob("*.json"):
            try:
                with open(file_path, 'r') as f:
                    message = Message.from_json(f.read())
                # Skip messages from self
                if message.sender == agent_id:
                    continue
                if since is None or message.timestamp > since:
                    messages.append(message)
            except Exception:
                continue

        # Sort by timestamp and priority
        messages.sort(key=lambda m: (m.timestamp, -m.priority))
        return messages

    def start(self):
        """Start polling thread."""
        super().start()
        self._poll_thread = Thread(target=self._poll_loop, daemon=True)
        self._poll_thread.start()

    def stop(self):
        """Stop polling thread."""
        super().stop()
        if self._poll_thread:
            self._poll_thread.join(timeout=5)

    def _poll_loop(self):
        """Poll for new messages and deliver to subscribers."""
        # Track processed message IDs to avoid duplicates
        processed_messages: set = set()
        max_processed_cache = 1000  # Limit cache size

        # Get messages from last 30 seconds on startup
        last_check = datetime.now() - timedelta(seconds=30)
        last_cleanup = datetime.now()
        cleanup_interval = 600  # Cleanup every 10 minutes

        # Cache for message file modification times
        last_scan_time = 0
        scan_interval = 5.0  # Only scan files every 5 seconds minimum

        while self.running:
            try:
                current_time = datetime.now()
                current_timestamp = current_time.timestamp()

                # Rate limit file scanning
                if current_timestamp - last_scan_time < scan_interval:
                    time.sleep(0.1)
                    continue

                last_scan_time = current_timestamp

                with self._lock:
                    subscribers_copy = dict(self.subscribers)

                # No subscribers, skip processing
                if not subscribers_copy:
                    time.sleep(2.0)
                    continue

                # Collect all messages once per poll cycle
                all_messages = {}
                for agent_id in subscribers_copy.keys():
                    messages = self.get_messages_for(agent_id, last_check)
                    if messages:
                        all_messages[agent_id] = messages

                # Process messages for each agent
                for agent_id, messages in all_messages.items():
                    callbacks = subscribers_copy.get(agent_id, [])
                    if not callbacks:
                        continue

                    for message in messages:
                        # Skip already processed messages (by ID)
                        if message.message_id in processed_messages:
                            continue

                        processed_messages.add(message.message_id)

                        # Limit cache size to prevent memory growth
                        if len(processed_messages) > max_processed_cache:
                            processed_messages = set(list(processed_messages)[-max_processed_cache//2:])

                        for callback in callbacks:
                            try:
                                callback(message)
                            except Exception as e:
                                print(f"Callback error for {agent_id}: {e}")

                # Periodic cleanup of old messages
                if (current_time - last_cleanup).total_seconds() > cleanup_interval:
                    self.cleanup_old_messages(max_age_hours=1)
                    last_cleanup = current_time

                last_check = current_time
                time.sleep(1.0)  # Sleep between cycles

            except Exception as e:
                print(f"Poll loop error: {e}")
                time.sleep(2)

    def cleanup_old_messages(self, max_age_hours: int = 24):
        """Remove old message files.

        Args:
            max_age_hours: Maximum age of messages to keep.
        """
        cutoff = datetime.now() - timedelta(hours=max_age_hours)

        for dir_path in [self.broadcast_dir] + list(self.inbox_dir.iterdir()):
            if not dir_path.is_dir():
                continue
            for file_path in dir_path.glob("*.json"):
                try:
                    mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
                    if mtime < cutoff:
                        file_path.unlink()
                except Exception:
                    continue


class RedisMessageBus(MessageBus):
    """Redis-based message bus for distributed multi-agent communication."""

    def __init__(
        self,
        namespace: str = "torch_npu_agents",
        redis_host: str = "localhost",
        redis_port: int = 6379,
        redis_db: int = 0,
        redis_password: Optional[str] = None
    ):
        """Initialize Redis-based message bus.

        Args:
            namespace: Namespace for this bus instance.
            redis_host: Redis server host.
            redis_port: Redis server port.
            redis_db: Redis database number.
            redis_password: Redis password.
        """
        if not REDIS_AVAILABLE:
            raise ImportError(
                "Redis support requires 'redis' package. "
                "Install with: pip install redis"
            )

        super().__init__(namespace)
        self.redis_client = redis.Redis(
            host=redis_host,
            port=redis_port,
            db=redis_db,
            password=redis_password,
            decode_responses=True
        )
        self._pubsub = None
        self._listener_thread: Optional[Thread] = None

    def _get_channel_name(self, agent_id: str) -> str:
        """Get Redis channel name for an agent."""
        return f"{self.namespace}:agent:{agent_id}"

    def _get_broadcast_channel(self) -> str:
        """Get broadcast channel name."""
        return f"{self.namespace}:broadcast"

    def publish(self, message: Message) -> bool:
        """Publish message to Redis."""
        try:
            channel = (
                self._get_channel_name(message.recipient)
                if message.recipient
                else self._get_broadcast_channel()
            )
            self.redis_client.publish(channel, message.to_json())

            # Also store in history list
            history_key = f"{self.namespace}:history:{message.recipient or 'broadcast'}"
            self.redis_client.lpush(history_key, message.to_json())
            self.redis_client.ltrim(history_key, 0, 999)  # Keep last 1000

            return True
        except Exception as e:
            print(f"Failed to publish message: {e}")
            return False

    def subscribe(self, agent_id: str, callback: Callable[[Message], None]) -> bool:
        """Subscribe agent to receive messages."""
        with self._lock:
            if agent_id not in self.subscribers:
                self.subscribers[agent_id] = []
            self.subscribers[agent_id].append(callback)
        return True

    def unsubscribe(self, agent_id: str) -> bool:
        """Unsubscribe agent."""
        with self._lock:
            if agent_id in self.subscribers:
                del self.subscribers[agent_id]
        return True

    def get_messages_for(self, agent_id: str, since: Optional[datetime] = None) -> List[Message]:
        """Get message history for agent."""
        messages = []
        try:
            # Get direct messages
            history_key = f"{self.namespace}:history:{agent_id}"
            for msg_json in self.redis_client.lrange(history_key, 0, -1):
                try:
                    message = Message.from_json(msg_json)
                    if since is None or message.timestamp > since:
                        messages.append(message)
                except Exception:
                    continue

            # Sort by timestamp
            messages.sort(key=lambda m: m.timestamp)
        except Exception as e:
            print(f"Failed to get messages: {e}")

        return messages

    def start(self):
        """Start Redis pub/sub listener."""
        super().start()
        self._pubsub = self.redis_client.pubsub()
        self._listener_thread = Thread(target=self._listen_loop, daemon=True)
        self._listener_thread.start()

    def stop(self):
        """Stop Redis pub/sub listener."""
        super().stop()
        if self._pubsub:
            self._pubsub.close()
        if self._listener_thread:
            self._listener_thread.join(timeout=5)

    def _listen_loop(self):
        """Listen for Redis pub/sub messages."""
        # Subscribe to all agent channels and broadcast
        channels = [self._get_broadcast_channel()]

        while self.running:
            try:
                with self._lock:
                    for agent_id in self.subscribers.keys():
                        channels.append(self._get_channel_name(agent_id))

                if channels:
                    self._pubsub.subscribe(*channels)

                    for message in self._pubsub.listen():
                        if not self.running:
                            break
                        if message['type'] != 'message':
                            continue

                        try:
                            msg = Message.from_json(message['data'])
                            # Deliver to appropriate subscribers
                            with self._lock:
                                recipients = [msg.recipient] if msg.recipient else list(self.subscribers.keys())
                                for agent_id in recipients:
                                    if agent_id in self.subscribers:
                                        for callback in self.subscribers[agent_id]:
                                            try:
                                                callback(msg)
                                            except Exception as e:
                                                print(f"Callback error: {e}")
                        except Exception as e:
                            print(f"Message parsing error: {e}")

            except Exception as e:
                print(f"Listen loop error: {e}")
                time.sleep(1)


def create_message_bus(
    backend: str = "file",
    namespace: str = "torch_npu_agents",
    **kwargs
) -> MessageBus:
    """Factory function to create message bus.

    Args:
        backend: 'file' or 'redis'.
        namespace: Namespace for the bus.
        **kwargs: Additional arguments for specific backends.

    Returns:
        Configured message bus instance.
    """
    if backend == "file":
        return FileMessageBus(
            namespace=namespace,
            base_dir=kwargs.get("base_dir", ".agent_messages")
        )
    elif backend == "redis":
        return RedisMessageBus(
            namespace=namespace,
            redis_host=kwargs.get("redis_host", "localhost"),
            redis_port=kwargs.get("redis_port", 6379),
            redis_db=kwargs.get("redis_db", 0),
            redis_password=kwargs.get("redis_password")
        )
    else:
        raise ValueError(f"Unknown backend: {backend}")
