# Logic Flow

## Startup Sequence

```
main.py
  └── setup_logging()
  └── Instantiate: SystemState, AudioPlayer, Camera, ServoController, FiringRelay,
                   FaceDetector, FaceRecognizer, FaceTracker, FireController, AutonomousController
  └── Register SIGINT/SIGTERM → shutdown()
  └── camera.start()     → begins threaded frame capture
  └── servo.start()      → PCA9685 init, centre servos
  └── relay.start()      → GPIO setup, pin = INPUT (idle)
  └── detector.start()   → load Haar cascade XML
  └── recognizer.start() → load LBPH model if exists
  └── audio.play("init")
  └── autonomous.start() → 15 Hz engagement loop daemon thread
  └── uvicorn.run(app)   → blocks; handles HTTP on port 8080
```

## Autonomous Engagement Loop (15 Hz)

```
tick()
  ├── mode != AUTONOMOUS → skip
  ├── camera.get_frame()  → None → skip
  ├── detector.detect(frame) → faces[]
  │     └── empty → "mission_complete" sound if was tracking; reset tracker
  ├── tracker.largest_face(faces) → target rect
  ├── detector.extract_roi(frame, target) → gray ROI
  ├── recognizer.predict(roi) → (name, confidence)
  │     ├── name is not None (safe) → log, update state, skip engagement
  │     └── name is None (hostile):
  │           ├── first detection → audio.play("targeting")
  │           ├── tracker.compute_deltas(target) → (pan_δ, tilt_δ)
  │           ├── servo.move(pan_δ, tilt_δ)
  │           └── tracker.acquired AND cooldown elapsed:
  │                 └── fire_ctrl.attempt_fire()
  │                       ├── not armed → deny
  │                       ├── no ammo  → audio("out_of_ammo"), deny
  │                       └── fire:
  │                             ├── audio("engaging")
  │                             ├── relay.fire_*()
  │                             └── state.consume_ammo()
  └── update state.pan / state.tilt / state.tracking
```

## Face Registration Flow

```
Web UI → POST /api/mode {mode: "registration"}
  └── state.mode = REGISTRATION (autonomous loop idles)

POST /api/register/snapshot {name: "Alice"}
  └── camera.get_frame()
  └── cv2.imwrite(face_data/Alice/0001.png)

(repeat for N snapshots — recommend ≥ 20)

POST /api/register/train {name: "Alice"}
  └── load all .png files from face_data/Alice/
  └── recognizer.enroll("Alice", images)
        └── LBPH.train([...])
        └── save model.yml + labels.pkl

Switch back to Autonomous mode → Alice is now recognised as safe
```

## Graceful Shutdown

```
SIGINT / SIGTERM
  └── autonomous.stop()
  └── audio.play("shutdown")
  └── servo.stop()     → centre servos, deinit PCA9685
  └── relay.stop()     → pin = INPUT, GPIO cleanup
  └── camera.stop()    → join capture thread, release cap
  └── sys.exit(0)
```
