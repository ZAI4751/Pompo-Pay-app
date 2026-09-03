import { createSecureTokenStore } from "@/auth/secureStorage";

function fakeSecureStore() {
  const disk = new Map<string, string>();
  return {
    disk,
    getItemAsync: jest.fn(async (key: string) => disk.get(key) ?? null),
    setItemAsync: jest.fn(async (key: string, value: string) => {
      disk.set(key, value);
    }),
    deleteItemAsync: jest.fn(async (key: string) => {
      disk.delete(key);
    }),
  };
}

describe("createSecureTokenStore", () => {
  it("returns newly written tokens after logout without waiting on disk", async () => {
    const storage = fakeSecureStore();
    storage.deleteItemAsync.mockImplementation(async () => {
      // Simulate Android SecureStore ignoring the next write after delete.
    });
    storage.getItemAsync.mockImplementation(async () => null);

    const store = createSecureTokenStore(storage);
    await store.setTokens("access-1", "refresh-1");
    await store.clear();
    await store.setTokens("access-2", "refresh-2");

    expect(await store.getAccessToken()).toBe("access-2");
    expect(await store.getRefreshToken()).toBe("refresh-2");
  });

  it("does not re-read SecureStore after clear so stale disk values stay hidden", async () => {
    const storage = fakeSecureStore();
    const store = createSecureTokenStore(storage);
    await store.setTokens("access-1", "refresh-1");
    await store.clear();
    storage.disk.set("pompo.access_token", "stale-access");
    storage.disk.set("pompo.refresh_token", "stale-refresh");

    expect(await store.getAccessToken()).toBeNull();
    expect(await store.getRefreshToken()).toBeNull();
  });
});
