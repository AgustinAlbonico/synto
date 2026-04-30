# Workspace + Stack Detection — Planificación

## Resumen

El **Workspace** es la unidad fundamental de contexto de Synto. Representa la selección de una o más carpetas de un proyecto sobre las cuales la IA puede operar. Es el pegamento entre la interfaz de usuario y el contexto que reciben los agentes.

El **Stack Detector** analiza las carpetas del workspace y detecta automáticamente el stack tecnológico usado.

**Estado:** Planificación — no implementado

---

## 1. Concepto

Un **Workspace** es un contexto de trabajo definido por:

1. **Rutas de carpetas** — una o más paths del filesystem
2. **Metadata del proyecto** — nombre, descripción, tipo de proyecto
3. **Stack detectado** — frameworks, lenguajes, herramientas
4. **Configuración activa** — perfil de agente, variables de entorno asociadas

### ¿Por qué workspaces y no un solo proyecto?

El usuario trabaja con **monorepos** (pnpm/turbo) que incluyen backend y frontend en una sola estructura, pero también con proyectos separados donde backend y frontend viven en carpetas distintas. Un Workspace debe adaptarse a ambos escenarios sin forzar una estructura única.

```
Monorepo (todo junto):
  workspace/
    apps/
      frontend/
      backend/
    packages/
      shared/

Proyecto separado (múltiples carpetas):
  workspace/
    /mnt/c/Projects/sistema-odontologico/apps/api
    /mnt/c/Projects/sistema-odontologico/apps/web
```

---

## 2. Modelo de Datos

### Workspace

```typescript
interface Workspace {
  id: string;                    // UUID
  name: string;                  // "Sistema Odontológico"
  description?: string;          // "CRM para consultorio dental"
  paths: string[];               // ["/mnt/c/.../apps/api", "/mnt/c/.../apps/web"]
  type: 'monorepo' | 'polyrepo' | 'single';
  stack: DetectedStack;          // Ver sección 3
  createdAt: Date;
  updatedAt: Date;
  isActive: boolean;            // Solo uno activo a la vez
}

interface DetectedStack {
  frameworks: Framework[];
  languages: Language[];
  packageManagers: PackageManager[];
  databases: string[];           // ["postgresql", "redis"]
  infrastructure: string[];     // ["docker", "kubernetes"]
  tools: Tool[];
  monorepoManager?: string;      // "turbo", "nx", "pnpm-workspace"
}

interface Framework {
  name: string;                  // "React", "NestJS", "FastAPI"
  icon: string;                  // emoji: "⚛️", "🪿"
  version?: string;              // "18.2.0" (opcional)
  category: 'frontend' | 'backend' | 'mobile' | 'desktop' | 'other';
  detectedIn: string;            // Path donde se detectó
}

interface Language {
  name: string;                  // "TypeScript", "Python"
  icon: string;
  percentage?: number;            // % del proyecto (estimado)
  detectedIn: string;
}

interface PackageManager {
  name: string;                  // "pnpm", "npm", "poetry", "pip"
  icon: string;
  detectedIn: string;
}

interface Tool {
  name: string;                  // "turborepo", "tRPC", "Prisma"
  icon: string;
  category: 'build' | 'test' | 'lint' | 'orm' | 'api' | 'auth' | 'other';
  detectedIn: string;
}
```

---

## 3. Detección de Stack

### Algoritmo de Detección

La detección se ejecuta al crear o actualizar un Workspace. Sigue este orden:

```
1. Escanear package.json en cada path
   → Extraer dependencies, devDependencies
   → Clasificar por nombre (React, NestJS, Prisma, etc.)

2. Escanear archivos de config
   → turbo.json → monorepoManager: "turbo"
   → pnpm-workspace.yaml → packageManager: "pnpm"
   → nest-cli.json → framework: "NestJS"
   → vite.config.ts → framework: "Vite"
   → pyproject.toml → packageManager: "poetry"
   → requirements.txt / Pipfile → packageManager: "pip"
   → docker-compose.yml → infrastructure: "docker"
   → drizzle.config.ts → tool: "Drizzle ORM"

3. Escanear archivos de código
   → *.tsx, *.jsx → language: "JavaScript/TypeScript"
   → *.py → language: "Python"
   → *.java → language: "Java"
   → Contar extensiones por carpeta para estimar %

4. Clasificar y rankear
   → Frontend frameworks (React, Vue, Svelte, Next.js, Nuxt)
   → Backend frameworks (NestJS, Express, FastAPI, Django, Rails)
   → ORMs (Prisma, Drizzle, TypeORM, SQLAlchemy)
   → Build tools (Turborepo, Nx, Vite, Webpack, esbuild)
   → Test runners (Jest, Vitest, Playwright, Cypress)
   → Linters (ESLint, Prettier, Ruff, Pylint)
   → Auth (NextAuth, Passport, JWT, OAuth)
   → API (tRPC, GraphQL, REST, gRPC)
```

### Iconos por tecnología

```
Frameworks:
  ⚛️ React          🅽 Next.js       〰️ Svelte       🎲 Vue
  🪿 NestJS         🚀 FastAPI       🎯 Express      🐍 Django
  💎 Rails          🍃 Flask         ☄️ Nuxt         🏗️ Remix

Lenguajes:
  _ts TypeScript    _js JavaScript   🐍 Python       ☕ Java
  🦀 Rust           🔷 C#           🟣 Go           💎 Ruby

Package Managers:
  📦 npm            🧩 pnpm          🪢 yarn         🐍 pip
  🏺 poetry         🌊 bun

Build & Monorepo:
  🏎️ Turborepo      🦋 Nx            ⚡ Vite         📜 Webpack
  🪄 esbuild        🎯 tRPC

Databases & ORM:
  🐘 PostgreSQL      🐬 MySQL        🍃 MongoDB     🔷 Redis
  🔶 Prisma         🌊 Drizzle      🗄️ TypeORM     🐍 SQLAlchemy

Infrastructure:
  🐳 Docker         ☸️ Kubernetes    🌥️ AWS         ☁️ GCP
  🔥 Firebase       ⚪ Vercel        🟣 Railway

Testing:
  🃏 Jest           ⚗️ Vitest       🎭 Playwright  🦎 Cypress
  🧪 Pytest        🐍 Robot

Linting & Quality:
  🔍 ESLint        🎨 Prettier      🦜 Ruff         🔧 Pylint
  🧹 Biome

Auth:
  🔐 NextAuth       🛡️ Passport     🔑 JWT          🔓 OAuth

API:
  📡 tRPC           🔷 GraphQL      🌐 REST        📨 gRPC

AI / ML:
  🤖 LangChain      🧠 Transformers  🔥 PyTorch      🏀 TensorFlow
```

---

## 4. Comportamiento

### Creación de un Workspace

1. Usuario proporciona paths de carpetas
2. Se ejecuta detección de stack en paralelo por path
3. Se consolida el stack de todas las carpetas
4. Se persiste en SQLite

### Actualización del Stack

- Se re-detecta automáticamente cuando:
  - Se modifica `package.json` en cualquier path del workspace
  - Se modifica `turbo.json`, `pnpm-workspace.yaml`, etc.
  - El usuario lo solicita manualmente
- La detección es **incremental**: solo re escanea lo que cambió

---

## 5. Integración con el Orchestrator

Cuando un workspace está activo, su contexto se inyecta en el prompt del Supervisor:

```markdown
## Contexto Activo del Workspace

**Proyecto:** Sistema Odontológico
**Tipo:** Monorepo
**Paths:**
  - `/mnt/c/.../apps/api`
  - `/mnt/c/.../apps/web`

**Stack:**
- ⚛️ React 18 (apps/web)
- 🪿 NestJS (apps/api)
- 🔶 Prisma ORM (apps/api)
- 🐘 PostgreSQL
- 📦 pnpm + 🏎️ Turborepo
- 🐳 Docker

**Archivos relevantes:**
- `apps/api/src/main.ts`
- `apps/web/src/App.tsx`
```

---

## 6. Roadmap de Implementación

### Fase 1: Modelo y detección básica
- [ ] Definir esquema para `workspaces` en SQLite
- [ ] Crear `StackDetector` service
- [ ] Parser de `package.json` → frameworks
- [ ] Parser de archivos de config (turbo, pnpm-workspace, etc.)

### Fase 2: Persistencia
- [ ] CRUD completo de workspaces
- [ ] Deteección incremental (cache)

### Fase 3: Integración con Orchestrator
- [ ] Inyección de contexto del workspace en prompts de agentes
- [ ] Mostrar workspace activo en logs/UI

---

## 7. Decisiones de Diseño

| Decisión | Justificación |
|----------|---------------|
| SQLite local | El workspace es contexto local del usuario. No necesita sync. |
| Detección on-demand | Escanear filesystem es caro. Solo al crear/actualizar workspace. |
| Iconos como strings hardcodeados | Más simple que cargar un mapa externo. Fácil de mantener. |
| Paths como array, no como árbol | El usuario selecciona carpetas específicas. Un árbol sería overkill. |
| Un solo workspace activo | Evita ambigüedad. El supervisor recibe un solo contexto claro. |
| Monorepo vs Polyrepo detectado automáticamente | Se infiere de la estructura (turbo.json, pnpm-workspace.yaml, o paths que comparten ancestro). |

---

## 8. Notas

- La detección de stack debe ser **rápida** (< 2s para un monorepo promedio). Usar glob patterns optimizados y cache.
- Soportar paths en WSL (`/mnt/...`) y Windows (`C:/...`) indistintamente.
- Futuro: detectar también **patrones de arquitectura** (Clean Architecture, DDD, etc.) basándose en la estructura de carpetas.
