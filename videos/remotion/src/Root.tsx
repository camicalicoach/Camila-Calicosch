import { Composition, staticFile } from "remotion";
import { parseMedia } from "@remotion/media-parser";
import { Subtitulos, subtitulosSchema } from "./Subtitulos";

const FPS = 30;

export const RemotionRoot: React.FC = () => (
  <Composition
    id="Subtitulos"
    component={Subtitulos}
    fps={FPS}
    width={1080}
    height={1920}
    durationInFrames={FPS * 10}
    defaultProps={{
      video: "video.mp4",
      captions: "captions.json",
      msPorBloque: 1200,
    } satisfies subtitulosSchema}
    // Toma la duración del video que esté en public/
    calculateMetadata={async ({ props }) => {
      const { slowDurationInSeconds } = await parseMedia({
        src: staticFile(props.video),
        fields: { slowDurationInSeconds: true },
        acknowledgeRemotionLicense: true,
      });
      return { durationInFrames: Math.ceil(slowDurationInSeconds * FPS) };
    }}
  />
);
