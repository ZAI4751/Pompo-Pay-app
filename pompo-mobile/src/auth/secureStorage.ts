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

export const secureTokenStore: TokenStore = {
  async getAccessToken() {
    return SecureStore.getItemAsync(ACCESS_KEY, SECURE_OPTIONS);
  },
  async getRefreshToken() {
    return SecureStore.getItemAsync(REFRESH_KEY, SECURE_OPTIONS);
  },
  async setTokens(accessToken: string, refreshToken: string) {
    await SecureStore.setItemAsync(ACCESS_KEY, accessToken, SECURE_OPTIONS);
    await SecureStore.setItemAsync(REFRESH_KEY, refreshToken, SECURE_OPTIONS);
  },
  async clear() {
    await SecureStore.deleteItemAsync(ACCESS_KEY, SECURE_OPTIONS);
    await SecureStore.deleteItemAsync(REFRESH_KEY, SECURE_OPTIONS);
  },
};
