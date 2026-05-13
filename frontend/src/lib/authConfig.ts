import { Configuration, LogLevel } from "@azure/msal-browser";

export const msalConfig: Configuration = {
  auth: {
    clientId: "00000000-0000-0000-0000-000000000000",
    authority: "https://login.microsoftonline.com/00000000-0000-0000-0000-000000000000",
    redirectUri: "http://localhost:3000",
    postLogoutRedirectUri: "http://localhost:3000",
  },
  cache: {
    cacheLocation: "localStorage",
    storeAuthStateInCookie: false,
  },
  system: {
    loggerOptions: {
      logLevel: LogLevel.Warning,
    },
  },
};

export const loginRequest = {
  scopes: ["api://00000000-0000-0000-0000-000000000000/access_as_user"],
};

export const apiConfig = {
  baseUrl: "https://localhost:5001/api",
};
