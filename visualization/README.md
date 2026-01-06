### Event Visualization 

The repository provides three ways to inspect generated events: an interactive viewer, an event-to-video renderer, and a side-by-side comparison renderer.

#### Interactive event viewer

Activate the Torch environment and run the viewer from the repository root:

```bash
conda activate vid2e_torch

python visualization/viz_events.py \
  --input_dir working_dir/events \
  --shape 256 320
```

Arguments

- input_dir: Directory containing generated event files *.npz (e.g., 0000000000.npz, 0000000001.npz, ...).
- shape H W: Sensor/image resolution used for rendering the event frames. Set this to the resolution used during event simulation (i.e., the upsampled frame resolution).

#### Side-by-side comparison 

This script renders an events-only video first and then composes a synchronized side-by-side output with the reference video.

```bash
conda activate vid2e_torch

python visualization/render_comparison.py \
  --original_dir working_dir/original_test_videos_5s/240p_bw/walking_240p_bw.mp4 \
  --events_dir working_dir/events \
  --timestamps_dir working_dir/upsampled/timestamps.txt \
  --sensor_w 426 \
  --sensor_h 240 \
  --fps 240 \
  --tau_ms 20 \
  --output_dir out_1080p.mp4 \
  --gap 15
```

Arguments

- original_dir: Path to the original/reference video (shown on the left side).
- events_dir: Directory containing event files (*.npz) used for rendering the events video.
- timestamps_dir: Timestamp file (seconds, one per line) defining the render timeline/range for the events video.
- sensor_w: Event sensor width used during rendering.
- sensor_h: Event sensor height used during rendering.
- fps: Output FPS for the rendered events video (constant frame rate).
- tau_ms: Decay time constant for the event time-surface (smaller = faster fading).
- output_dir: Output path for the final combined side-by-side video.
- gap: Pixel spacing between the two videos in the final combined output.
  
#### Events-only video

Renders a constant-FPS MP4 directly from the event stream using an exponential decay time-surface.

```bash
conda activate vid2e_torch

python visualization/render_events.py \
  --events_dir working_dir/events \
  --timestamps working_dir/upsampled/timestamps.txt \
  --out output_events.mp4 \
  --sensor_w 426 \
  --sensor_h 240 \
  --fps 120 \
  --tau_ms 30 \
  --max_frames 1000
```

Arguments

- events_dir: Directory containing event files in .npz format (must include x, y, t, p arrays).
- timestamps: (optional) Path to a timestamps file (seconds, one per line) that defines the render timeline. If omitted, the renderer falls back to the timestamp range in the event files.
- out: Output path for the rendered MP4 file.
- sensor_w: Sensor width in pixels (must match the event coordinate system).
- sensor_h: Sensor height in pixels (must match the event coordinate system).
- fps: Output framerate (constant FPS).
- tau_ms: Exponential decay time constant in milliseconds (smaller = faster decay / less persistence).
- max_frames: (optional) Limit the number of rendered frames (useful for quick tests).

**Color scheme:**
- Blue: Positive polarity events.
- Red: Negative polarity events.
- Magenta: Overlap.
