# Synto Desktop (Tauri)

Synto ahora tiene una base de aplicación de escritorio con Tauri.

## Arquitectura actual

- Tauri abre la UI del Command Center en una ventana nativa.
- El backend sigue siendo FastAPI (`synto web`) en `127.0.0.1:8788`.
- La UI detecta si corre dentro de Tauri y usa `http://127.0.0.1:8788` como API base.
- El botón “Elegir carpeta” usa un comando nativo de Tauri (`pick_workspace_dir`) para obtener un path real del filesystem.

Esto es intencional: primero estabilizamos la experiencia desktop sin reescribir el runtime de agentes.

## Desarrollo

Desde la raíz del repo:

```bash
npm install
npm run desktop:dev
```

`desktop:dev` levanta el backend con:

```bash
python scripts/synto-web-dev.py --host 127.0.0.1 --port 8788
```

y después abre la ventana Tauri.

## Scripts útiles

```bash
npm run web:dev       # solo backend local en 8788
npm run desktop:dev   # backend + Tauri dev window
npm run desktop:build # empaquetado desktop (pendiente de sidecar Python real)
```

## Pendiente importante

El empaquetado final todavía necesita convertir el backend Python en sidecar distribuible. Para desarrollo ya alcanza con la virtualenv local; para release hay que elegir entre:

1. bundlear Python + dependencias como sidecar, o
2. convertir el runtime backend a binario/servicio instalable.

No conviene resolver eso antes de estabilizar la UX desktop.
