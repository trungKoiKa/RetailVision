package vn.retailvision.controller.device;

import java.util.List;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;
import vn.retailvision.dto.response.DeviceView;
import vn.retailvision.service.device.DeviceQueryService;

@RestController
@RequestMapping("/api/devices")
public class DeviceController {

    private final DeviceQueryService devices;

    public DeviceController(DeviceQueryService devices) {
        this.devices = devices;
    }

    @GetMapping
    public List<DeviceView> list() {
        return devices.devices();
    }
}
