"""Kết nối MQTT (paho 2.x) và bản thay thế dùng cho test.

`MqttLink` chạy luồng mạng riêng của paho; callback chỉ đẩy dữ liệu nhận được vào hàng đợi
để vòng xử lý chính đọc, không chạm vào trạng thái của pipeline.

Khi mất kết nối, bản tin QoS 1 được paho giữ trong RAM (tối đa MAX_QUEUED) và gửi lại khi nối lại.
Bản tin QoS 0 (state) bị bỏ. Không có nơi lưu bền trên edge: edge tắt đột ngột thì mất phần chưa gửi.
"""

from __future__ import annotations

import json
import queue
import sys
from typing import Callable, Optional, Protocol

from retailvision.messaging.payloads import Message

MAX_QUEUED = 5000
KEEPALIVE_S = 15


class Link(Protocol):
    inbox: "queue.Queue[tuple[str, bytes]]"

    def publish(self, message: Message) -> None: ...

    def close(self, final: Optional[Message] = None) -> None: ...


def encode(payload: dict) -> bytes:
    return json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


class MqttLink:
    def __init__(
        self,
        host: str,
        port: int,
        client_id: str,
        username: Optional[str],
        password: Optional[str],
        will: Optional[Message],
        on_connect_messages: Callable[[], list[Message]],
        subscriptions: list[tuple[str, int]],
    ) -> None:
        import paho.mqtt.client as mqtt  # import muộn: test analytics không cần paho

        self._mqtt = mqtt
        self.inbox: "queue.Queue[tuple[str, bytes]]" = queue.Queue()
        self._on_connect_messages = on_connect_messages
        self._subscriptions = subscriptions
        self._closing = False
        client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=client_id, protocol=mqtt.MQTTv311)
        if username:
            client.username_pw_set(username, password)
        if will is not None:
            client.will_set(will.topic, encode(will.payload), qos=will.qos, retain=will.retain)
        client.reconnect_delay_set(min_delay=1, max_delay=30)
        client.max_queued_messages_set(MAX_QUEUED)
        client.on_connect = self._on_connect
        client.on_message = self._on_message
        client.on_disconnect = self._on_disconnect
        self._client = client
        client.connect_async(host, port, keepalive=KEEPALIVE_S)
        client.loop_start()

    def _on_connect(self, client, userdata, flags, reason_code, properties) -> None:
        if reason_code.is_failure:
            print(f"MQTT: kết nối bị từ chối: {reason_code}", file=sys.stderr)
            return
        for topic, qos in self._subscriptions:
            client.subscribe(topic, qos)
        for message in self._on_connect_messages():
            self.publish(message)
        print("MQTT: đã kết nối", file=sys.stderr)

    def _on_disconnect(self, client, userdata, flags, reason_code, properties) -> None:
        if not self._closing:
            print(f"MQTT: mất kết nối ({reason_code}); tự nối lại", file=sys.stderr)

    def _on_message(self, client, userdata, msg) -> None:
        self.inbox.put((msg.topic, bytes(msg.payload)))

    def publish(self, message: Message):
        return self._client.publish(message.topic, encode(message.payload), qos=message.qos, retain=message.retain)

    def close(self, final: Optional[Message] = None) -> None:
        """Ngắt kết nối chủ động (Last Will sẽ không chạy), nên gửi trước bản tin OFFLINE `final`."""
        self._closing = True
        if final is not None:
            info = self.publish(final)
            try:
                info.wait_for_publish(timeout=3)
            except (ValueError, RuntimeError):
                pass  # chưa nối được: bỏ qua
        self._client.disconnect()
        self._client.loop_stop()


class ListLink:
    """Thay thế trong test: ghi lại bản tin đã gửi, cho phép nhét bản tin đến."""

    def __init__(self) -> None:
        self.sent: list[Message] = []
        self.inbox: "queue.Queue[tuple[str, bytes]]" = queue.Queue()
        self.closed = False

    def publish(self, message: Message) -> None:
        self.sent.append(message)

    def close(self, final: Optional[Message] = None) -> None:
        if final is not None:
            self.sent.append(final)
        self.closed = True
