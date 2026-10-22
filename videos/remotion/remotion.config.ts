import { Config } from "@remotion/cli/config";

// En la nube se usa el Chromium preinstalado (la descarga de Remotion está bloqueada)
if (process.env.REMOTION_BROWSER_EXECUTABLE) {
  Config.setBrowserExecutable(process.env.REMOTION_BROWSER_EXECUTABLE);
}
