import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import App from "./App";
import "./index.css";
import { ThemeProvider } from "./lib/theme-provider";
import { Auth0ProviderWithNavigation } from "./lib/auth0-provider";
import { AuthProvider } from "./lib/auth-context";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <ThemeProvider defaultTheme="dark" storageKey="airweave-ui-theme">
      <BrowserRouter>
        <Auth0ProviderWithNavigation>
          <AuthProvider>
            <App />
          </AuthProvider>
        </Auth0ProviderWithNavigation>
      </BrowserRouter>
    </ThemeProvider>
  </React.StrictMode>
);
