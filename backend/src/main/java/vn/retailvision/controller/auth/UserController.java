package vn.retailvision.controller.auth;

import jakarta.validation.Valid;
import java.util.List;
import org.springframework.http.HttpStatus;
import org.springframework.security.core.Authentication;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PatchMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;
import vn.retailvision.dto.request.CreateUserRequest;
import vn.retailvision.dto.request.UpdateUserRequest;
import vn.retailvision.dto.response.UserView;
import vn.retailvision.service.auth.UserService;

/** Quản lý tài khoản: chỉ ADMIN (kiểm trong SecurityConfig). Không xóa tài khoản, chỉ vô hiệu hóa. */
@RestController
@RequestMapping("/api/users")
public class UserController {

    private final UserService users;

    public UserController(UserService users) {
        this.users = users;
    }

    @GetMapping
    public List<UserView> list() {
        return users.list();
    }

    @PostMapping
    @ResponseStatus(HttpStatus.CREATED)
    public UserView create(@Valid @RequestBody CreateUserRequest body) {
        return users.create(body);
    }

    @PatchMapping("/{id}")
    public UserView update(@PathVariable long id, @Valid @RequestBody UpdateUserRequest body, Authentication authentication) {
        return users.update(id, body, authentication.getName());
    }
}
