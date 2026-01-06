# Video to Events: Recycling Video Datasets for Event Cameras
## Extended Visualization & Comparison Tools

**Extended and maintained by Marvin Hermann, Research Assistant at MaiRo Lab, Karlsruhe Institute of Technology (KIT)**

This repository extends the original [Video to Events](https://github.com/uzh-rpg/rpg_vid2e) implementation by Gehrig et al. (CVPR 2020) with enhanced event visualization capabilities, including event-based video generation and side-by-side comparison tools for event-based vision research.

---

## About

This project builds upon the video-to-events conversion method described in:
> Daniel Gehrig, Mathias Gehrig, Javier Hidalgo-Carrió, Davide Scaramuzza  
> **"Video to Events: Recycling Video Datasets for Event Cameras"**  
> IEEE Conference on Computer Vision and Pattern Recognition (CVPR), 2020  
> [Paper](http://rpg.ifi.uzh.ch/docs/CVPR20_Gehrig.pdf)

The original work enables synthetic event generation from conventional video datasets, making it possible to leverage existing video data for event camera research.

---

## My Additions

This fork provides significant extensions to the original codebase:

- **Event-based video generation**: Generate high-quality videos directly from event streams with improved temporal coherence and visual quality
- **Side-by-side comparison visualization**: Synchronized playback of original frames and generated event representations for qualitative analysis
- **Enhanced rendering pipeline**: Optimized event accumulation and frame reconstruction for better visualization of fast motion and dynamic scenes
- **Improved configuration options**: Extended parameter control for contrast thresholds, temporal windows, and output formats
- **Dual conda environment**: Seperated upsampling and event generation in corresponding environments, ensuring future proofed versioning and collision avoidance

These tools were developed as part of ongoing robotics research at the MaiRo Lab (Robotics Institute Germany member) to facilitate event camera evaluation and algorithm development.

---

## Original Authors & Citation

If you use this code in an academic context, please cite the original work:

```bibtex
@InProceedings{Gehrig_2020_CVPR,
  author = {Daniel Gehrig and Mathias Gehrig and Javier Hidalgo-Carri\'o and Davide Scaramuzza},
  title = {Video to Events: Recycling Video Datasets for Event Cameras},
  booktitle = {{IEEE} Conf. Comput. Vis. Pattern Recog. (CVPR)},
  month = {June},
  year = {2020}
}
```

## Installation

For an indepth explaination see the [installation.md](installation.md)

## upsampling
*This package provides code for adaptive upsampling with frame interpolation based on [Super-SloMo](https://people.cs.umass.edu/~hzjiang/projects/superslomo/)*

Consult the [README](upsampling/README.md) for detailed instructions and examples.

## esim\_py
*This package exposes python bindings for [ESIM](http://rpg.ifi.uzh.ch/docs/CORL18_Rebecq.pdf) which can be used within a training loop.*

For detailed instructions and example consult the [README](esim_py/README.md)

## esim\_torch
*This package exposes python bindings for [ESIM](http://rpg.ifi.uzh.ch/docs/CORL18_Rebecq.pdf) with GPU support.*

For detailed instructions and example consult the [README](esim_torch/README.md)

## visualization
*This package provides advanced event visualization services.*
For detailed instructions and example consult the [README](visualization/README.md)

## Usage

### Upsamling:

- **Video input**: sequence folder contains a video file; `fps.txt` optional (FPS inferred from metadata if missing, this sometimes leads to inaccurate results).
- **Image input**: sequence folder contains `fps.txt` + `imgs/00000001.png ...`; `fps.txt` required.
- **Output**: `output_dir/<seq>/imgs/` = upsampled frames (original + interpolated in one sequence), `timestamps.txt` = timestamp (seconds) per output image.

Execute in repo base directory:

##### On CPU:

```bash
conda activate vid2e

device=cpu
CUDA_VISIBLE_DEVICES=$device python upsampling/upsample.py \
  --input_dir=example/original \
  --output_dir=example/upsampled
```

##### On GPU:

```bash
conda activate vid2e

device=0
CUDA_VISIBLE_DEVICES=$device python upsampling/upsample.py \
  --input_dir=example/original \
  --output_dir=example/upsampled
```

this will generate all between frames accoardingly to the paper. => one pixel position change equals one frame change

### Event generating:

- **Input**: upsampled sequences `seq/imgs/*.png` + `seq/timestamps.txt` (seconds).​
- **Output**: `seq/0000000000.npz ...` where each `.npz` stores arrays `t, x, y, p` (timestamp, pixel coords, polarity).​
- **CT+ / CT-**: positive/negative contrast threshold (event triggers when brightness change crosses threshold); lower → more events, higher → fewer events.​
- **Refractory**: per-pixel dead time after events (ns); 0 disables it.

Execute in repo base directory:

```bash
conda activate vid2e_torch

python esim_torch/scripts/generate_events.py --input_dir=example/upsampled \
                                     --output_dir=example/events \
                                     --contrast_threshold_neg=0.2 \
                                     --contrast_threshold_pos=0.2 \
                                     --refractory_period_ns=0
```

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
conda activate vid2e

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
