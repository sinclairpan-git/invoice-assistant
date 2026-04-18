import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import type { PropsWithChildren } from "react";

import { getCurrentActor, getErrorMessage } from "./api";
import type { CurrentActor } from "./types";

const FALLBACK_ACTOR: CurrentActor = {
  actor_id: "local-operator",
  display_name: "本机管理员",
  roles: [],
};

interface OperatorSettingsValue {
  currentActor: CurrentActor;
  defaultOperatorName: string;
  loading: boolean;
  error: string | null;
  refreshCurrentActor: () => Promise<void>;
}

const OperatorSettingsContext = createContext<OperatorSettingsValue | null>(null);

export function OperatorSettingsProvider({ children }: PropsWithChildren) {
  const [currentActor, setCurrentActor] = useState<CurrentActor>(FALLBACK_ACTOR);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refreshCurrentActor = useCallback(async () => {
    setLoading(true);
    try {
      const actor = await getCurrentActor();
      setCurrentActor(actor);
      setError(null);
    } catch (loadError) {
      setCurrentActor(FALLBACK_ACTOR);
      setError(getErrorMessage(loadError));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refreshCurrentActor();
  }, [refreshCurrentActor]);

  const contextValue = useMemo(
    () => ({
      currentActor,
      defaultOperatorName: currentActor.display_name,
      loading,
      error,
      refreshCurrentActor,
    }),
    [currentActor, error, loading, refreshCurrentActor],
  );

  return <OperatorSettingsContext.Provider value={contextValue}>{children}</OperatorSettingsContext.Provider>;
}

export function useOperatorSettings(): OperatorSettingsValue {
  const context = useContext(OperatorSettingsContext);
  if (!context) {
    throw new Error("useOperatorSettings must be used within OperatorSettingsProvider.");
  }
  return context;
}
