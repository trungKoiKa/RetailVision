import { describe, expect, it } from "vitest";
import { formatAge, formatCount, formatDateTime, formatTime } from "./format";

describe("format", () => {
  it("đổi UTC sang giờ Việt Nam (UTC+7)", () => {
    expect(formatTime("2026-11-02T10:15:03Z")).toBe("17:15:03");
  });

  it("qua nửa đêm giờ Việt Nam thì sang ngày mới", () => {
    expect(formatDateTime("2026-11-02T17:00:00Z")).toContain("03/11/2026");
    expect(formatDateTime("2026-11-02T16:59:59Z")).toContain("02/11/2026");
  });

  it("thiếu giá trị thì hiện —", () => {
    expect(formatDateTime(null)).toBe("—");
    expect(formatTime(undefined)).toBe("—");
    expect(formatAge(null)).toBe("—");
    expect(formatAge(Number.NaN)).toBe("—");
  });

  it("tuổi dữ liệu", () => {
    expect(formatAge(0.84)).toBe("0,8 giây");
    expect(formatAge(12.4)).toBe("12 giây");
    expect(formatAge(185)).toBe("3 phút 05 giây");
  });

  it("số người null không thành 0", () => {
    expect(formatCount(null)).toBe("—");
    expect(formatCount(undefined)).toBe("—");
    expect(formatCount(0)).toBe("0"); // 0 thật là 0
    expect(formatCount(5)).toBe("5");
  });
});
