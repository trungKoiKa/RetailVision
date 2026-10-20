package vn.retailvision.controller.auth;

import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import jakarta.validation.Valid;
import org.springframework.http.HttpStatus;
import org.springframework.security.authentication.AuthenticationManager;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.AuthenticationException;
import org.springframework.security.core.GrantedAuthority;
import org.springframework.security.core.context.SecurityContext;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.security.web.context.SecurityContextRepository;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;
import vn.retailvision.dto.request.ChangePasswordRequest;
import vn.retailvision.dto.request.LoginRequest;
import vn.retailvision.dto.response.MeResponse;
import vn.retailvision.exception.ApiException;
import vn.retailvision.security.LoginAttemptService;
import vn.retailvision.service.auth.UserService;

@RestController
@RequestMapping("/api/auth")
public class AuthController {

    private final AuthenticationManager authentication;
    private final SecurityContextRepository contexts;
    private final LoginAttemptService attempts;
    private final UserService users;

    public AuthController(
            AuthenticationManager authentication,
            SecurityContextRepository contexts,
            LoginAttemptService attempts,
            UserService users) {
        this.authentication = authentication;
        this.contexts = contexts;
        this.attempts = attempts;
        this.users = users;
    }

    @PostMapping("/login")
    public MeResponse login(@Valid @RequestBody LoginRequest body, HttpServletRequest request, HttpServletResponse response) {
        String username = body.username().trim().toLowerCase();
        if (attempts.isLocked(username)) {
            throw new ApiException(HttpStatus.TOO_MANY_REQUESTS, "TOO_MANY_ATTEMPTS", "Sai quá nhiều lần, thử lại sau ít phút");
        }
        Authentication result;
        try {
            result = authentication.authenticate(UsernamePasswordAuthenticationToken.unauthenticated(username, body.password()));
        } catch (AuthenticationException e) {
            attempts.recordFailure(username);
            // cùng một thông báo cho tên không tồn tại, sai mật khẩu và tài khoản bị khoá
            throw new ApiException(HttpStatus.UNAUTHORIZED, "BAD_CREDENTIALS", "Tên đăng nhập hoặc mật khẩu không đúng");
        }
        attempts.recordSuccess(username);
        if (request.getSession(false) != null) {
            request.changeSessionId(); // chống session fixation
        }
        SecurityContext context = SecurityContextHolder.createEmptyContext();
        context.setAuthentication(result);
        SecurityContextHolder.setContext(context);
        contexts.saveContext(context, request, response);
        users.touchLogin(username);
        return toMe(result);
    }

    @PostMapping("/logout")
    @ResponseStatus(HttpStatus.NO_CONTENT)
    public void logout(HttpServletRequest request) {
        if (request.getSession(false) != null) {
            request.getSession(false).invalidate();
        }
        SecurityContextHolder.clearContext();
    }

    @GetMapping("/me")
    public MeResponse me(Authentication authentication) {
        return toMe(authentication);
    }

    @PostMapping("/password")
    @ResponseStatus(HttpStatus.NO_CONTENT)
    public void changePassword(@Valid @RequestBody ChangePasswordRequest body, Authentication authentication) {
        users.changeOwnPassword(authentication.getName(), body.currentPassword(), body.newPassword());
    }

    private static MeResponse toMe(Authentication auth) {
        String role = auth.getAuthorities().stream()
                .map(GrantedAuthority::getAuthority)
                .filter(a -> a.startsWith("ROLE_"))
                .map(a -> a.substring("ROLE_".length()))
                .findFirst()
                .orElse("");
        return new MeResponse(auth.getName(), role);
    }
}
