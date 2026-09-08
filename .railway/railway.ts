import { Service, type EnvVar } from "https://railway.com/.railway/railway.ts";

export const service = new Service("forge")
  .setBuildCommand("pip install .")
  .setStartCommand("python3 -m forge serve --host 0.0.0.0 --port ${PORT} --token ${FORGE_TOKEN}")
  .setMounts({ name: "forge-journal", mountPath: "/www" });

export const FORGE_TOKEN: EnvVar = { value: "changeme-local-only-not-production" };
