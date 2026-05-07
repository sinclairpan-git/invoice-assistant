import { computed, readonly, ref } from "vue";

import { getCurrentActor, getErrorMessage } from "./api";
import type { CurrentActor } from "./types";

const FALLBACK_ACTOR: CurrentActor = {
  actor_id: "local-operator",
  display_name: "本机管理员",
  roles: [],
};

const currentActor = ref<CurrentActor>(FALLBACK_ACTOR);
const loading = ref(false);
const error = ref<string | null>(null);
let pending: Promise<void> | null = null;

export async function refreshCurrentActor() {
  if (pending) {
    return pending;
  }
  loading.value = true;
  pending = getCurrentActor()
    .then((actor) => {
      currentActor.value = actor;
      error.value = null;
    })
    .catch((loadError: unknown) => {
      currentActor.value = FALLBACK_ACTOR;
      error.value = getErrorMessage(loadError);
    })
    .finally(() => {
      loading.value = false;
      pending = null;
    });
  return pending;
}

export function useOperatorSettings() {
  return {
    currentActor: readonly(currentActor),
    defaultOperatorName: computed(() => currentActor.value.display_name),
    loading: readonly(loading),
    error: readonly(error),
    refreshCurrentActor,
  };
}
