package vn.retailvision.support;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;
import java.util.stream.Stream;

/** Đọc ví dụ trong contracts/examples (nguồn sự thật). Tên file: {prefix}__{ca}.json. */
public final class ContractExamples {

    private static final Path ROOT = Path.of("..", "contracts", "examples");

    public record Example(String prefix, String name, byte[] bytes) {}

    private ContractExamples() {}

    public static List<Example> valid(String... prefixes) {
        return load("valid", prefixes);
    }

    public static List<Example> invalid(String... prefixes) {
        return load("invalid", prefixes);
    }

    public static byte[] validBytes(String fileName) {
        return read(ROOT.resolve("valid").resolve(fileName));
    }

    private static List<Example> load(String folder, String... prefixes) {
        List<String> wanted = List.of(prefixes);
        try (Stream<Path> files = Files.list(ROOT.resolve(folder))) {
            return files.filter(p -> p.getFileName().toString().endsWith(".json"))
                    .filter(p -> wanted.contains(prefixOf(p)))
                    .sorted()
                    .map(p -> new Example(prefixOf(p), p.getFileName().toString(), read(p)))
                    .toList();
        } catch (IOException e) {
            throw new IllegalStateException("Không đọc được " + ROOT.resolve(folder).toAbsolutePath(), e);
        }
    }

    private static String prefixOf(Path p) {
        return p.getFileName().toString().split("__", 2)[0];
    }

    private static byte[] read(Path p) {
        try {
            return Files.readAllBytes(p);
        } catch (IOException e) {
            throw new IllegalStateException("Không đọc được " + p.toAbsolutePath(), e);
        }
    }

    public static String text(byte[] bytes) {
        return new String(bytes, StandardCharsets.UTF_8);
    }
}
