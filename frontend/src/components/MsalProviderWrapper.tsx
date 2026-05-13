"use client";

import { useEffect, useState, useRef } from "react";
import {
  MsalProvider,
  useMsal,
  useIsAuthenticated,
} from "@azure/msal-react";
import {
  PublicClientApplication,
  InteractionStatus,
} from "@azure/msal-browser";
import { msalConfig, loginRequest } from "@/lib/authConfig";
import { setMsalInstance } from "@/lib/api";

const msalInstance = new PublicClientApplication(msalConfig);
setMsalInstance(msalInstance);

function AuthGuard({ children }: { children: React.ReactNode }) {
  const { instance, inProgress } = useMsal();
  const isAuthenticated = useIsAuthenticated();
  const redirected = useRef(false);

  useEffect(() => {
    if (
      !isAuthenticated &&
      inProgress === InteractionStatus.None &&
      !redirected.current
    ) {
      redirected.current = true;
      instance.loginRedirect(loginRequest);
    }
  }, [isAuthenticated, inProgress, instance]);

  if (!isAuthenticated) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-slate-950 text-slate-500">
        Redirigiendo al inicio de sesión...
      </div>
    );
  }

  return <>{children}</>;
}

export default function MsalProviderWrapper({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <MsalProvider instance={msalInstance}>
      <AuthGuard>{children}</AuthGuard>
    </MsalProvider>
  );
}
