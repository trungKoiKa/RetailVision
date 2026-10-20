package vn.retailvision.dto.request;

import jakarta.validation.constraints.Pattern;

/** Trường nào null thì giữ nguyên. */
public record UpdateUserRequest(@Pattern(regexp = "ADMIN|MANAGER") String role, Boolean enabled, String password) {}
