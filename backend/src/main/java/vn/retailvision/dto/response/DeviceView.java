package vn.retailvision.dto.response;

import java.time.Instant;

/** Thiết bị chưa từng báo status có status UNKNOWN và các trường còn lại null. */
public record DeviceView(String deviceId, String status, String version, Boolean clockSynced, Instant lastSeenAt) {}
