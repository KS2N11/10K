import { Configuration, PopupRequest } from "@azure/msal-browser";

/**
 * Configuration object to be passed to MSAL instance on creation. 
 * For a full list of MSAL.js configuration parameters, visit:
 * https://github.com/AzureAD/microsoft-authentication-library-for-js/blob/dev/lib/msal-browser/docs/configuration.md 
 */

// Azure AD Configuration from environment variables
export const msalConfig: Configuration = {
  auth: {
    clientId: import.meta.env.VITE_AZURE_CLIENT_ID || "7973a9b5-f08d-43eb-9474-1e453a5d3199", // Application (client) ID from Azure Portal
    authority: import.meta.env.VITE_AZURE_AUTHORITY || "https://login.microsoftonline.com/74c3a4b1-a2a5-4e48-9d7b-434f36d335ed", // Use your specific tenant ID, not 'common'
    redirectUri: import.meta.env.VITE_AZURE_REDIRECT_URI || window.location.origin, // Must be registered as a redirect URI in Azure Portal
    postLogoutRedirectUri: window.location.origin, // Where to redirect after logout
  },
  cache: {
    cacheLocation: "sessionStorage", // This configures where your cache will be stored
    storeAuthStateInCookie: false, // Set this to "true" if you are having issues on IE11 or Edge
  },
  system: {
    loggerOptions: {
      loggerCallback: (level, message, containsPii) => {
        if (containsPii) {
          return;
        }
        switch (level) {
          case 0: // LogLevel.Error
            console.error(message);
            return;
          case 1: // LogLevel.Warning
            console.warn(message);
            return;
          case 2: // LogLevel.Info
            // Only log info in development mode
            if (import.meta.env.DEV) {
              console.info(message);
            }
            return;
          case 3: // LogLevel.Verbose
            // Only log verbose in development mode
            if (import.meta.env.DEV) {
              console.debug(message);
            }
            return;
        }
      },
      logLevel: import.meta.env.PROD ? 1 : 2 // Warning level in production, Info level in development
    }
  }
};

/**
 * Scopes you add here will be prompted for user consent during sign-in.
 * By default, MSAL.js will add OIDC scopes (openid, profile, email) to any login request.
 */
export const loginRequest: PopupRequest = {
  scopes: ["User.Read"] // Request access to read user profile
};

/**
 * Add here the endpoints and scopes for the web API you would like to access.
 */
export const apiConfig = {
  scopes: ["User.Read"],
  uri: import.meta.env.VITE_API_URL || "http://localhost:8000"
};
