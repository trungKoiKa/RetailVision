package vn.retailvision.controller.settings;

import jakarta.validation.Valid;
import org.springframework.http.HttpStatus;
import org.springframework.security.core.Authentication;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;
import vn.retailvision.dto.request.SettingsRequest;
import vn.retailvision.dto.response.SettingsViews;
import vn.retailvision.service.settings.SettingsService;

/** Đổi ngưỡng vận hành (P1). Quyền MANAGER/ADMIN kiểm trong SecurityConfig. */
@RestController
@RequestMapping("/api/settings")
public class SettingsController {

    private final SettingsService settings;

    public SettingsController(SettingsService settings) {
        this.settings = settings;
    }

    @GetMapping
    public SettingsViews.Overview get() {
        return settings.overview();
    }

    /** 202: đã gửi cho edge, kết quả (APPLIED/REJECTED) đến sau; theo dõi bằng GET /api/settings. */
    @PutMapping
    @ResponseStatus(HttpStatus.ACCEPTED)
    public SettingsViews.Request put(@Valid @RequestBody SettingsRequest body, Authentication authentication) {
        return settings.submit(body, authentication.getName());
    }
}
