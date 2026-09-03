import fs from "fs";
import path from "path";

function walkTsx(dir: string, files: string[] = []): string[] {
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      walkTsx(full, files);
    } else if (entry.name.endsWith(".tsx")) {
      files.push(full);
    }
  }
  return files;
}

describe("persistent bottom navigation architecture", () => {
  const appDir = path.join(__dirname, "..", "app");

  test("customer and merchant layouts mount AppShell around the stack", () => {
    const customerLayout = fs.readFileSync(path.join(appDir, "customer", "_layout.tsx"), "utf8");
    const merchantLayout = fs.readFileSync(path.join(appDir, "merchant", "_layout.tsx"), "utf8");
    expect(customerLayout).toContain("<AppShell>");
    expect(customerLayout).toContain("<Stack");
    expect(merchantLayout).toContain("<AppShell>");
    expect(merchantLayout).toContain("<Stack");
  });

  test("individual screens do not render BottomNav inside the animated stack", () => {
    const screens = walkTsx(appDir).filter((file) => !file.endsWith(`${path.sep}_layout.tsx`));
    const offenders = screens.filter((file) => fs.readFileSync(file, "utf8").includes("<BottomNav"));
    expect(offenders).toEqual([]);
  });
});
