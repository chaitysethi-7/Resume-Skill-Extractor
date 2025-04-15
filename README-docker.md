# Resume Skill Extractor - Docker Usage

## Build the Docker Image
```sh
docker build -t resume-skill-extractor .
```

## Run the App (Linux/Mac with X11)
```sh
docker run -it \
    -e DISPLAY=$DISPLAY \
    -v /tmp/.X11-unix:/tmp/.X11-unix \
    resume-skill-extractor
```

## Run the App (Windows with X Server)
1. Install VcXsrv or Xming and start it.
2. Find your host IP (e.g., 192.168.1.100).
3. Run:
```sh
docker run -it -e DISPLAY=192.168.1.100:0.0 resume-skill-extractor
```

- The GUI will appear on your host if X11 forwarding is set up.
- For persistent storage, map a volume to `/app`.

## Requirements
- Docker
- X11 server (for GUI display)

---

**Note:**
- This container runs a Tkinter GUI. For headless/server-only use, consider a web-based interface in the future.
