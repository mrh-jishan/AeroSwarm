export type LaunchLlmProvider = "openai" | "gemini";

export interface LaunchSettings {
  providerConnectionId: string;
  llmProvider: LaunchLlmProvider;
  managerModel: string;
  agentModel: string;
}

export const PROVIDER_DEFAULTS: Record<
  LaunchLlmProvider,
  { managerModel: string; agentModel: string }
> = {
  openai: {
    managerModel: "gpt-4o",
    agentModel: "gpt-4o",
  },
  gemini: {
    managerModel: "gemini-2.5-flash",
    agentModel: "gemini-2.5-flash",
  },
};

const STORAGE_KEY = "aeroswarm.launch.settings";

export function getDefaultLaunchSettings(): LaunchSettings {
  return {
    providerConnectionId: "",
    llmProvider: "gemini",
    managerModel: PROVIDER_DEFAULTS.gemini.managerModel,
    agentModel: PROVIDER_DEFAULTS.gemini.agentModel,
  };
}

export function normalizeLaunchSettings(
  input?: Partial<LaunchSettings> | null,
): LaunchSettings {
  const defaults = getDefaultLaunchSettings();
  const llmProvider =
    input?.llmProvider === "openai" || input?.llmProvider === "gemini"
      ? input.llmProvider
      : defaults.llmProvider;

  return {
    providerConnectionId: input?.providerConnectionId ?? defaults.providerConnectionId,
    llmProvider,
    managerModel:
      input?.managerModel?.trim() || PROVIDER_DEFAULTS[llmProvider].managerModel,
    agentModel: input?.agentModel?.trim() || PROVIDER_DEFAULTS[llmProvider].agentModel,
  };
}

export function loadLaunchSettings(): LaunchSettings {
  if (typeof window === "undefined") {
    return getDefaultLaunchSettings();
  }

  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) {
      return getDefaultLaunchSettings();
    }
    return normalizeLaunchSettings(JSON.parse(raw) as Partial<LaunchSettings>);
  } catch {
    return getDefaultLaunchSettings();
  }
}

export function saveLaunchSettings(settings: LaunchSettings): void {
  if (typeof window === "undefined") {
    return;
  }

  window.localStorage.setItem(
    STORAGE_KEY,
    JSON.stringify(normalizeLaunchSettings(settings)),
  );
}
