# throughline — frontend

This is the React + Vite + TypeScript + Tailwind v4 frontend for **throughline**.

For setup, the full picture, and how everything fits together, see the [root README](../README.md). The easiest way to run the whole app (Ollama + backend + frontend) is `./run.sh` from the repo root.

## Frontend dev commands

Run these from the repo root:

```bash
npm --prefix app install        # install dependencies
npm --prefix app run dev        # dev server at http://localhost:5173
npm --prefix app run build      # production build (tsc -b + vite build)
npm --prefix app run lint       # eslint
npm --prefix app run preview    # preview the production build
```

The frontend talks to the backend API at http://127.0.0.1:8000 (Swagger at `/docs`).
