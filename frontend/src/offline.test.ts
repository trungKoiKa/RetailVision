import { readFileSync, readdirSync, statSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";

/** T13: mất Internet, LAN còn, web vẫn chạy. Trang không được nạp tài nguyên (font, CDN, script) từ ngoài. */
const ROOT = join(__dirname, "..");

function sourceFiles(dir: string): string[] {
  return readdirSync(dir).flatMap((name) => {
    const path = join(dir, name);
    if (statSync(path).isDirectory()) return sourceFiles(path);
    return /\.(css|html|tsx?)$/.test(name) && !/\.test\.tsx?$/.test(name) ? [path] : [];
  });
}

describe("không phụ thuộc Internet", () => {
  it("index.html và mã nguồn không tham chiếu URL ngoài", () => {
    const files = [join(ROOT, "index.html"), ...sourceFiles(join(ROOT, "src"))];
    const offenders = files.flatMap((file) => {
      const text = readFileSync(file, "utf-8");
      // URL tuyệt đối http(s) trong mã (bỏ qua chú thích dòng và namespace SVG/XML)
      return text
        .split("\n")
        .filter((line) => !line.trim().startsWith("//") && !line.trim().startsWith("*"))
        .filter((line) => /https?:\/\/(?!www\.w3\.org)/.test(line))
        .map((line) => `${file}: ${line.trim()}`);
    });
    expect(offenders).toEqual([]);
  });

  it("mọi lời gọi API đi qua đường dẫn tương đối /api", () => {
    const text = sourceFiles(join(ROOT, "src"))
      .map((f) => readFileSync(f, "utf-8"))
      .join("\n");
    const calls = [...text.matchAll(/apiFetch(?:<[^>]*>)?\(\s*["'`]([^"'`]+)/g)].map((m) => m[1]);
    expect(calls.length).toBeGreaterThan(0);
    for (const path of calls) expect(path.startsWith("/api/")).toBe(true);
  });
});
