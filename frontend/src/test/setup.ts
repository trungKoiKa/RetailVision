import "@testing-library/jest-dom/vitest";
import { cleanup } from "@testing-library/react";
import { afterEach, vi } from "vitest";

// Recharts dùng ResizeObserver, jsdom không có
class ResizeObserverStub {
  observe() {}
  unobserve() {}
  disconnect() {}
}
vi.stubGlobal("ResizeObserver", ResizeObserverStub);

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  vi.stubGlobal("ResizeObserver", ResizeObserverStub);
});
