package vn.retailvision.security;

import com.fasterxml.jackson.databind.ObjectMapper;
import jakarta.servlet.DispatcherType;
import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import java.io.IOException;
import java.util.Map;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.http.HttpMethod;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.security.authentication.AuthenticationManager;
import org.springframework.security.authentication.ProviderManager;
import org.springframework.security.authentication.dao.DaoAuthenticationProvider;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.config.annotation.web.configuration.EnableWebSecurity;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.security.web.SecurityFilterChain;
import org.springframework.security.web.authentication.www.BasicAuthenticationFilter;
import org.springframework.security.web.context.HttpSessionSecurityContextRepository;
import org.springframework.security.web.context.SecurityContextRepository;
import org.springframework.security.web.csrf.CookieCsrfTokenRepository;
import org.springframework.security.web.csrf.CsrfToken;
import org.springframework.security.web.csrf.CsrfTokenRequestAttributeHandler;
import org.springframework.web.filter.OncePerRequestFilter;

/**
 * Đăng nhập bằng session cookie (HttpOnly, SameSite=Lax), CSRF bằng cookie XSRF-TOKEN + header X-XSRF-TOKEN,
 * phân quyền kiểm ở API. Lỗi trả JSON 401/403, không chuyển hướng.
 */
@Configuration
@EnableWebSecurity
public class SecurityConfig {

    @Bean
    public PasswordEncoder passwordEncoder() {
        return new BCryptPasswordEncoder();
    }

    @Bean
    public SecurityContextRepository securityContextRepository() {
        return new HttpSessionSecurityContextRepository();
    }

    @Bean
    public AuthenticationManager authenticationManager(AppUserDetailsService users, PasswordEncoder encoder) {
        DaoAuthenticationProvider provider = new DaoAuthenticationProvider(users);
        provider.setPasswordEncoder(encoder);
        return new ProviderManager(provider);
    }

    @Bean
    public SecurityFilterChain filterChain(HttpSecurity http, ObjectMapper json, SecurityContextRepository contexts) throws Exception {
        CsrfTokenRequestAttributeHandler csrfHandler = new CsrfTokenRequestAttributeHandler();
        csrfHandler.setCsrfRequestAttributeName(null); // token đọc ngay khi cần, để filter bên dưới đặt cookie
        http.csrf(csrf -> csrf
                        .csrfTokenRepository(CookieCsrfTokenRepository.withHttpOnlyFalse())
                        .csrfTokenRequestHandler(csrfHandler))
                .addFilterAfter(new CsrfCookieFilter(), BasicAuthenticationFilter.class)
                .securityContext(sc -> sc.securityContextRepository(contexts))
                .httpBasic(basic -> basic.disable())
                .formLogin(form -> form.disable())
                .logout(logout -> logout.disable()) // đăng xuất qua POST /api/auth/logout
                .authorizeHttpRequests(auth -> auth
                        .dispatcherTypeMatchers(DispatcherType.ERROR).permitAll()
                        .requestMatchers(HttpMethod.GET, "/api/health").permitAll()
                        .requestMatchers("/api/auth/login").permitAll()
                        .requestMatchers("/api/users/**").hasRole("ADMIN")
                        .requestMatchers("/api/auth/**").authenticated()
                        .requestMatchers("/api/**").hasAnyRole("MANAGER", "ADMIN")
                        .anyRequest().denyAll())
                .exceptionHandling(ex -> ex
                        .authenticationEntryPoint((req, res, e) -> writeError(json, res, HttpStatus.UNAUTHORIZED, "UNAUTHENTICATED", "Chưa đăng nhập"))
                        .accessDeniedHandler((req, res, e) -> writeError(json, res, HttpStatus.FORBIDDEN, "FORBIDDEN", "Không đủ quyền")));
        return http.build();
    }

    static void writeError(ObjectMapper json, HttpServletResponse res, HttpStatus status, String code, String message) throws IOException {
        res.setStatus(status.value());
        res.setContentType(MediaType.APPLICATION_JSON_VALUE);
        res.setCharacterEncoding("UTF-8");
        json.writeValue(res.getWriter(), Map.of("error", code, "message", message));
    }

    /** Buộc CSRF token được tạo và cookie XSRF-TOKEN được gửi ở mọi phản hồi (kể cả 401), để SPA đọc được. */
    static final class CsrfCookieFilter extends OncePerRequestFilter {
        @Override
        protected void doFilterInternal(HttpServletRequest request, HttpServletResponse response, FilterChain chain)
                throws ServletException, IOException {
            CsrfToken token = (CsrfToken) request.getAttribute(CsrfToken.class.getName());
            if (token != null) {
                token.getToken();
            }
            chain.doFilter(request, response);
        }
    }
}
