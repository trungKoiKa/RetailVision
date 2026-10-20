package vn.retailvision.dto.response;

import java.time.Instant;

public record UserView(Long id, String username, String role, boolean enabled, Instant createdAt, Instant lastLoginAt) {}
