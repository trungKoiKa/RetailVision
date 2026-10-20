package vn.retailvision.dto.request;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Pattern;

public record CreateUserRequest(
        @NotBlank String username, @NotBlank String password, @NotBlank @Pattern(regexp = "ADMIN|MANAGER") String role) {}
