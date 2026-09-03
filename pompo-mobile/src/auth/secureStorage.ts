import * as SecureStore from "expo-secure-store";

const ACCESS_KEY = "pompo.access_token";
const REFRESH_KEY = "pompo.refresh_token";

const SECURE_OPTIONS: SecureStore.SecureStoreOptions = {
  keychainAccessible: SecureStore.AFTER_FIRST_UNLOCK,
};

export interface TokenStore {
  getAccessToken(): Promise<string | null>;
  getRefreshToken(): Promise<string | null>;
  setTokens(accessToken: string, refreshToken: string): Promise<void>;
  clear(): Promise<void>;
}

interface SecureStoreLike {
  getItemAsync(key: string, options?: SecureStore.SecureStoreOptions): Promise<string | null>;
  setItemAsync(key: string, value: string, options?: SecureStore.SecureStoreOptions): Promise<void>;
  deleteItemAsync(key: string, options?: SecureStore.SecureStoreOptions): Promise<void>;
}

/**
 * Process-local cache in front of SecureStore.
 *
 * Android SecureStore can return stale or empty values after delete-then-set
 * of the same key. Login after logout reads tokens immediately for /auth/me,
 * so the cache is the source of truth for the current process.
 */
export function createSecureTokenStore(storage: SecureStoreLike = SecureStore): TokenStore {
  let cache: { access: string | null; refresh: string | null } | undefined;

  async function readThrough(): Promise<{ access: string | null; refresh: string | null }> {
    if (cache !== undefined) {
      return cache;
    }
    const [access, refresh] = await Promise.all([
      storage.getItemAsync(ACCESS_KEY, SECURE_OPTIONS),
      storage.getItemAsync(REFRESH_KEY, SECURE_OPTIONS),
    ]);
    cache = { access, refresh };
    return cache;
  }

  return {
    async getAccessToken() {
      return (await readThrough()).access;
    },
    async getRefreshToken() {
      return (await readThrough()).refresh;
    },
    async setTokens(accessToken, refreshToken) {
      cache = { access: accessToken, refresh: refreshToken };
      await storage.setItemAsync(ACCESS_KEY, accessToken, SECURE_OPTIONS);
      await storage.setItemAsync(REFRESH_KEY, refreshToken, SECURE_OPTIONS);
    },
    async clear() {
      cache = { access: null, refresh: null };
      await storage.deleteItemAsync(ACCESS_KEY, SECURE_OPTIONS);
      await storage.deleteItemAsync(REFRESH_KEY, SECURE_OPTIONS);
    },
  };
}

export const secureTokenStore: TokenStore = createSecureTokenStore();
