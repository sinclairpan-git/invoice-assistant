import { createContext, useCallback, useContext, useMemo, useState } from "react";
import type { PropsWithChildren } from "react";


const STORAGE_KEY = "invoice-assistant/default-operator-name";
const DEFAULT_OPERATOR_NAME = "本机管理员";

interface OperatorSettingsValue {
  defaultOperatorName: string;
  setDefaultOperatorName: (value: string) => void;
}

const OperatorSettingsContext = createContext<OperatorSettingsValue | null>(null);

function readInitialOperatorName(): string {
  if (typeof window === "undefined") {
    return DEFAULT_OPERATOR_NAME;
  }
  const saved = window.localStorage.getItem(STORAGE_KEY);
  return saved?.trim() || DEFAULT_OPERATOR_NAME;
}

export function OperatorSettingsProvider({ children }: PropsWithChildren) {
  const [defaultOperatorName, setDefaultOperatorNameState] = useState<string>(readInitialOperatorName);

  const setDefaultOperatorName = useCallback((value: string) => {
    const nextValue = value.trim() || DEFAULT_OPERATOR_NAME;
    setDefaultOperatorNameState(nextValue);
    if (typeof window !== "undefined") {
      window.localStorage.setItem(STORAGE_KEY, nextValue);
    }
  }, []);

  const contextValue = useMemo(
    () => ({
      defaultOperatorName,
      setDefaultOperatorName,
    }),
    [defaultOperatorName, setDefaultOperatorName],
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
