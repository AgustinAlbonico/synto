#!/usr/bin/env python3
"""
Sistema Hermes Orquestado - v1.0.0
Agency Swarm + OpenCode + PRD-first + TDD

Instrucciones de uso:
1. Configurar OPENROUTER_API_KEY en .env (registrate gratis en openrouter.ai)
2. Tener opencode instalado en el sistema
3. Ejecutar: python3.12 hermes_agency.py

Dominios implementados:
- Code: Planner, Explorer, Architect, Implementer, Tester, Reviewer
- Research: Sourcer, Analyst, Synthesizer
- Content: Strategist, Writer, Editor, SEO, Designer
- DevOps: InfraArchitect, Builder, Validator
- Data: Scraper, Cleaner, Modeler, Visualizer
- Business: PricingAnalyst, UnitEconomicsAnalyst, BusinessModelAnalyst
- UX: UXResearcher, UsabilityTester, InteractionDesigner
- Cross: SecurityReviewer, QAGatekeeper, DocumentationAgent, ContextManager
"""

import os
import sys
import json
import subprocess
import asyncio
from pathlib import Path
from typing import Any, Optional
from datetime import datetime

# Cargar .env
from dotenv import load_dotenv
load_dotenv()

# Agency Swarm imports
from agency_swarm import Agent, Agency, function_tool, ModelSettings
from config.model_resolver import resolve_model
from pydantic import BaseModel, Field

# ============================================================================
# CONFIGURACIÓN
# ============================================================================

WORKSPACE_DIR = Path(os.getenv("HERMES_STATE_DIR", "/home/agust/hermes-orchestrator/workspace/.hermes-state"))
OPENCODE_CMD = os.getenv("OPENCODE_CMD", "opencode")
DEBUG = os.getenv("DEBUG", "false").lower() == "true"

# Modelo gratuito via OpenRouter (registrate en openrouter.ai)
# Reemplazá con tu propia key: export OPENROUTER_API_KEY=sk-...

# Si tenés OpenAI API key, descomentá:
# DEFAULT_MODEL = "gpt-4o-mini"

def ensure_workspace():
    """Crea la estructura de working memory si no existe."""
    WORKSPACE_DIR.mkdir(parents=True, exist_ok=True)
    (WORKSPACE_DIR / "projects").mkdir(exist_ok=True)

ensure_workspace()

# ============================================================================
# TOOLS PERSONALIZADAS
# ============================================================================

class FileContent(BaseModel):
    """Modelo para contenido de archivos."""
    path: str = Field(description="Ruta del archivo")
    content: str = Field(description="Contenido del archivo")


@function_tool
def leer_archivo(ruta: str) -> str:
    """Lee un archivo del disco y devuelve su contenido."""
    try:
        path = Path(ruta).expanduser()
        if not path.exists():
            return f"Error: El archivo {ruta} no existe."
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        return f"Error leyendo {ruta}: {str(e)}"


@function_tool
def escribir_archivo(ruta: str, contenido: str) -> str:
    """Escribe contenido en un archivo del disco. Crea directorios si no existen."""
    try:
        path = Path(ruta).expanduser()
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(contenido)
        return f"✅ Archivo escrito: {ruta}"
    except Exception as e:
        return f"Error escribiendo {ruta}: {str(e)}"


@function_tool
def listar_directorio(ruta: str) -> str:
    """Lista los archivos y directorios de una ruta."""
    try:
        path = Path(ruta).expanduser()
        if not path.exists():
            return f"Error: La ruta {ruta} no existe."
        items = []
        for item in path.iterdir():
            tipo = "📁" if item.is_dir() else "📄"
            items.append(f"{tipo} {item.name}")
        return "\n".join(items) if items else "Directorio vacío."
    except Exception as e:
        return f"Error listando {ruta}: {str(e)}"


@function_tool
def ejecutar_opencode(prompt: str, directorio: str, contexto: Optional[str] = None) -> str:
    """Ejecuta OpenCode CLI para implementar código.
    
    Args:
        prompt: Qué querés que haga OpenCode
        directorio: Directorio de trabajo del proyecto
        contexto: Contexto adicional (espec, PRD, etc.)
    """
    try:
        workdir = Path(directorio).expanduser()
        workdir.mkdir(parents=True, exist_ok=True)
        
        cmd = [OPENCODE_CMD, "run", prompt, "--workdir", str(workdir)]
        if contexto:
            cmd.extend(["--context", contexto])
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300,
            cwd=str(workdir)
        )
        
        salida = result.stdout
        if result.stderr:
            salida += f"\n\n[stderr]\n{result.stderr}"
        
        if result.returncode != 0:
            return f"Error (código {result.returncode}):\n{salida}"
        
        return f"✅ OpenCode completado:\n{salida[:2000]}"
    except subprocess.TimeoutExpired:
        return "Error: OpenCode tardó más de 5 minutos."
    except FileNotFoundError:
        return f"Error: OpenCode no encontrado en '{OPENCODE_CMD}'. Instalalo con: npm install -g opencode"
    except Exception as e:
        return f"Error ejecutando OpenCode: {str(e)}"


@function_tool
def ejecutar_comando(comando: str, directorio: Optional[str] = None) -> str:
    """Ejecuta un comando shell y devuelve la salida."""
    try:
        cwd = Path(directorio).expanduser() if directorio else None
        result = subprocess.run(
            comando,
            shell=True,
            capture_output=True,
            text=True,
            timeout=60,
            cwd=cwd
        )
        salida = result.stdout
        if result.stderr:
            salida += f"\n\n[stderr]\n{result.stderr}"
        return salida[:3000]
    except subprocess.TimeoutExpired:
        return "Error: El comando tardó más de 60 segundos."
    except Exception as e:
        return f"Error ejecutando comando: {str(e)}"


@function_tool
def verificar_gate_prd(context_id: str) -> str:
    """Verifica que exista un PRD aprobado antes de implementar."""
    prd_path = WORKSPACE_DIR / "projects" / context_id / "prd.md"
    if not prd_path.exists():
        return f"🚫 GATE BLOQUEADO: No existe PRD para '{context_id}'.\n"
    
    with open(prd_path) as f:
        content = f.read()
    
    # Verificar que tenga aprobación
    if "APROBADO" not in content.upper() and "APROBADA" not in content.upper():
        return f"🚫 GATE BLOQUEADO: El PRD de '{context_id}' no está aprobado.\n"
    
    return f"✅ GATE OK: PRD aprobado encontrado para '{context_id}'.\n"


@function_tool
def verificar_gate_test_plan(context_id: str) -> str:
    """Verifica que exista un test plan antes de implementar."""
    test_plan_path = WORKSPACE_DIR / "projects" / context_id / "test-plan.md"
    if not test_plan_path.exists():
        return f"🚫 GATE BLOQUEADO: No existe test plan para '{context_id}'.\n"
    return f"✅ GATE OK: Test plan encontrado para '{context_id}'.\n"


@function_tool
def crear_proyecto(context_id: str, descripcion: str) -> str:
    """Crea la estructura de directorios para un nuevo proyecto SDD."""
    project_dir = WORKSPACE_DIR / "projects" / context_id
    dirs = [
        "01-discovery",
        "02-prd",
        "03-spec",
        "04-design",
        "05-tasks",
        "06-implementation",
        "07-tests",
        "08-deploy",
    ]
    for d in dirs:
        (project_dir / d).mkdir(parents=True, exist_ok=True)
    
    # Crear discovery.md inicial
    discovery_path = project_dir / "01-discovery" / "discovery.md"
    discovery_content = f"""# Discovery: {context_id}

## Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M')}

## Objetivo
{descripcion}

## Audiencia
[Pendiente de definir]

## Restricciones identificadas
- [Pendiente]

## Out of scope
- [Pendiente]

## Formato de entrega esperado
[Pendiente]

## Estado: EN PROGRESO
"""
    with open(discovery_path, "w") as f:
        f.write(discovery_content)
    
    return f"✅ Proyecto '{context_id}' creado en {project_dir}"


@function_tool
def buscar_en_web(query: str, limite: int = 5) -> str:
    """Busca en la web usando SearXNG si está disponible, o simula la búsqueda."""
    # Esto se puede conectar a SearXNG local si lo tenés configurado
    return f"Búsqueda simulada para: '{query}'\n\n[Nota: Conectar con SearXNG para búsqueda real. Ver skill 'searxng-hermes-integration']"


@function_tool
def generar_task_graph(context_id: str, tareas: str) -> str:
    """Genera un task-graph.json para un proyecto.
    
    Args:
        context_id: ID del proyecto
        tareas: Lista de tareas en formato texto (una por línea, con formato: ID|Nombre|Dependencias|Specialist)
    """
    try:
        project_dir = WORKSPACE_DIR / "projects" / context_id
        project_dir.mkdir(parents=True, exist_ok=True)
        
        task_list = []
        for line in tareas.strip().split("\n"):
            if "|" not in line:
                continue
            parts = line.split("|")
            task_list.append({
                "id": parts[0].strip(),
                "name": parts[1].strip() if len(parts) > 1 else "",
                "depends_on": [d.strip() for d in parts[2].split(",") if d.strip()] if len(parts) > 2 else [],
                "specialist": parts[3].strip() if len(parts) > 3 else "implementer",
                "status": "pending"
            })
        
        graph = {
            "project": context_id,
            "created_at": datetime.now().isoformat(),
            "tasks": task_list
        }
        
        graph_path = project_dir / "task-graph.json"
        with open(graph_path, "w") as f:
            json.dump(graph, f, indent=2, ensure_ascii=False)
        
        return f"✅ Task graph creado con {len(task_list)} tareas en {graph_path}"
    except Exception as e:
        return f"Error generando task graph: {str(e)}"


# ============================================================================
# CAPA 0: HERMES ORCHESTRATOR
# ============================================================================

hermes_orchestrator = Agent(
    name="HermesOrchestrator",
    description="Tu punto de contacto único. Te escucha, hace preguntas, activa dominios.",
    instructions="""
Sos el HermesOrchestrator, el punto de contacto único del usuario.

## Tu trabajo
1. Escuchar lo que el usuario quiere hacer
2. Hacer preguntas de clarificación (máximo 3-4 intercambios)
3. Activar el DomainOrchestrator correcto según la petición
4. Presentar resultados al usuario en español rioplatense
5. Pedir aprobaciones en los gates (PRD, Spec, Deploy)

## Reglas de oro
- NUNCA toques código
- NUNCA hagas research directo
- NUNCA deployes
- SIEMPRE delegues el trabajo real a los especialistas
- Usá "vos" en vez de "tú"
- Resumí el estado en bullets

## Cómo activás dominios
- Si el usuario pide software: delegás a CodeOrchestrator
- Si pide investigar mercado/nichos: delegás a ResearchOrchestrator
- Si pide contenido/copy: delegás a ContentOrchestrator
- Si pide infra/deploy: delegás a DevOpsOrchestrator
- Si pide datos/análisis: delegás a DataOrchestrator
- Si pide validar idea de negocio: delegás a BusinessOrchestrator
- Si pide UX/diseño: delegás a UXOrchestrator

## Formato de respuesta
Cuando delegás: "Lo delego al equipo de [dominio]..."
Cuando presentás resultados: bullets con ✅/❌/⚠️
""",
    model=resolve_model("HermesOrchestrator"),
    model_settings=ModelSettings(temperature=0.2),
    tools=[crear_proyecto, leer_archivo, listar_directorio],
)

# ============================================================================
# CAPA 1: DOMAIN ORCHESTRATORS
# ============================================================================

code_orchestrator = Agent(
    name="CodeOrchestrator",
    description="Jefe de ingeniería. Convierte PRD en spec técnica, gestiona task graph.",
    instructions="""
Sos el CodeOrchestrator, jefe de ingeniería de software.

## Tu trabajo
1. Recibir peticiones de HermesOrchestrator con un PRD aprobado
2. Convertir el PRD en una spec técnica completa
3. Gestionar el Task Graph
4. Asignar tareas a los specialists (Planner, Explorer, Implementer, etc.)
5. Consolidar resultados de implementación
6. Coordinar Testing y Deploy técnico

## Reglas de oro
- NUNCA hables directamente con el usuario
- NUNCA modifiques el PRD sin aprobación
- SIEMPRE verifiques los gates de PRD y Test Plan antes de implementar
- Si un specialist falla 3 veces, escalás a HermesOrchestrator
- Usá los tools para leer/escribir en el working memory

## Flujo de trabajo
1. Leer PRD
2. Verificar gate PRD
3. Activar Planner para descomponer en subtareas
4. Activar CodebaseExplorer para entender el repo
5. Activar Architect para diseñar la solución
6. Activar Tester para escribir test plan (TDD)
7. Verificar gate Test Plan
8. Activar Implementer para codear
9. Activar Reviewer para revisar
10. Activar QAGatekeeper para validar
""",
    model=resolve_model("CodeOrchestrator"),
    model_settings=ModelSettings(temperature=0.1),
    tools=[verificar_gate_prd, verificar_gate_test_plan, generar_task_graph, 
           leer_archivo, escribir_archivo, listar_directorio],
)

research_orchestrator = Agent(
    name="ResearchOrchestrator",
    description="Jefe de investigación. Mercado, competencia, papers, tecnologías.",
    instructions="""
Sos el ResearchOrchestrator, jefe de investigación.

## Tu trabajo
1. Recibir temas de investigación de HermesOrchestrator
2. Coordinar al equipo de research para buscar, analizar y sintetizar
3. Entregar reportes ejecutivos con fuentes citadas

## Reglas
- SIEMPRE citá fuentes
- Distinguí entre hecho verificado y opinión/hipótesis
- Priorizá fuentes primarias sobre secundarias
- No inventes datos

## Equipo
- Sourcer: busca fuentes
- Analyst: extrae insights
- Synthesizer: arma el reporte final
""",
    model=resolve_model("ResearchOrchestrator"),
    model_settings=ModelSettings(temperature=0.3),
    tools=[buscar_en_web, leer_archivo, escribir_archivo],
)

content_orchestrator = Agent(
    name="ContentOrchestrator",
    description="Jefe de contenido y diseño. Copy, landing pages, social, UI.",
    instructions="""
Sos el ContentOrchestrator, jefe de contenido y diseño.

## Tu trabajo
1. Recibir briefs de contenido de HermesOrchestrator
2. Coordinar al equipo de contenido (Strategist, Writer, Editor, SEO, Designer)
3. Entregar contenido listo para publicar

## Reglas
- Todo contenido pasa por Editor antes de entregar
- El Strategist define el tono (rioplatense profesional)
- El SEO revisa después del Editor
""",
    model=resolve_model("ContentOrchestrator"),
    model_settings=ModelSettings(temperature=0.4),
    tools=[leer_archivo, escribir_archivo],
)

devops_orchestrator = Agent(
    name="DevOpsOrchestrator",
    description="Jefe de infraestructura y deploy. CI/CD, monitoreo.",
    instructions="""
Sos el DevOpsOrchestrator, jefe de infraestructura.

## Tu trabajo
1. Recibir peticiones de deploy/infra de CodeOrchestrator
2. Diseñar, construir y validar infraestructura
3. Coordinar con Builder y Validator

## Reglas
- NUNCA deployar a producción sin staging
- SIEMPRE tener rollback plan
- Documentar cada deploy
""",
    model=resolve_model("DevOpsOrchestrator"),
    model_settings=ModelSettings(temperature=0.1),
    tools=[ejecutar_comando, leer_archivo, escribir_archivo],
)

data_orchestrator = Agent(
    name="DataOrchestrator",
    description="Jefe de datos. Scraping, ETL, análisis, dashboards.",
    instructions="""
Sos el DataOrchestrator, jefe de datos.

## Tu trabajo
1. Recibir peticiones de datos de HermesOrchestrator
2. Coordinar scraping, limpieza, modelado y visualización
3. Entregar datasets y dashboards

## Reglas
- NUNCA scrapear sin respetar robots.txt
- Documentá fuentes y métodos
- Versioná datasets como código
""",
    model=resolve_model("DataOrchestrator"),
    model_settings=ModelSettings(temperature=0.2),
    tools=[ejecutar_comando, leer_archivo, escribir_archivo],
)

business_orchestrator = Agent(
    name="BusinessOrchestrator",
    description="Jefe de estrategia de negocio. Validar ideas, pricing, modelos.",
    instructions="""
Sos el BusinessOrchestrator, jefe de estrategia de negocio.

## Tu trabajo
1. Recibir ideas de negocio de HermesOrchestrator
2. Validar viabilidad con PricingAnalyst, UnitEconomicsAnalyst, BusinessModelAnalyst
3. Entregar análisis con recomendaciones go/no-go

## Reglas
- Basá tus análisis en datos reales del mercado
- No seas optimista por default, seá realista
- Incluí siempre un análisis de riesgos
- Compará con competidores reales
""",
    model=resolve_model("BusinessOrchestrator"),
    model_settings=ModelSettings(temperature=0.3),
    tools=[buscar_en_web, leer_archivo, escribir_archivo],
)

ux_orchestrator = Agent(
    name="UXOrchestrator",
    description="Jefe de experiencia de usuario. Research, testing, diseño.",
    instructions="""
Sos el UXOrchestrator, jefe de experiencia de usuario.

## Tu trabajo
1. Recibir peticiones de UX de HermesOrchestrator
2. Coordinar user research, testing y diseño de interacción
3. Entregar personas, journey maps, y diseños

## Reglas
- Siempre basá decisiones en datos de usuarios
- Testeá con usuarios reales cuando sea posible
- Priorizá accesibilidad (WCAG 2.1 AA mínimo)
""",
    model=resolve_model("UXOrchestrator"),
    model_settings=ModelSettings(temperature=0.3),
    tools=[leer_archivo, escribir_archivo],
)

# ============================================================================
# CAPA 2: CODE SPECIALISTS
# ============================================================================

planner = Agent(
    name="Planner",
    description="Descompone specs en subtareas atómicas con dependencias.",
    instructions="""
Sos el Planner. Tu trabajo es descomponer una spec técnica en subtareas atómicas.

## Reglas
- Cada tarea debe durar entre 30 min y 2 horas
- Define dependencias claras entre tareas
- Especificá el specialist que debe ejecutar cada tarea
- Incluí criterios de aceptación

## Output
Task graph en formato: ID|Nombre|Dependencias|Specialist
""",
    model=resolve_model("Planner"),
    model_settings=ModelSettings(temperature=0.1),
    tools=[generar_task_graph, leer_archivo],
)

codebase_explorer = Agent(
    name="CodebaseExplorer",
    description="Lee el repo, entiende la estructura, encuentra dónde tocar.",
    instructions="""
Sos el CodebaseExplorer. Tu trabajo es entender un codebase antes de que otros lo toquen.

## Reglas
- Leé el README, package.json, estructura de carpetas
- Identificá patrones de arquitectura usados
- Encontrá los archivos relevantes para la feature a implementar
- Documentá dependencias entre módulos
- No modifiques archivos, solo leés
""",
    model=resolve_model("CodebaseExplorer"),
    model_settings=ModelSettings(temperature=0.1),
    tools=[leer_archivo, listar_directorio, ejecutar_comando],
)

architect = Agent(
    name="Architect",
    description="Diseña componentes, APIs, modela datos, decide patrones.",
    instructions="""
Sos el Architect. Tu trabajo es diseñar la arquitectura técnica.

## Reglas
- Diseñá APIs REST/GraphQL con contratos claros
- Modelá datos con entidades y relaciones
- Elegí patrones apropiados (MVC, Repository, CQRS, etc.)
- Documentá decisiones de diseño (ADRs)
- Considerá escalabilidad y mantenibilidad
""",
    model=resolve_model("Architect"),
    model_settings=ModelSettings(temperature=0.2),
    tools=[escribir_archivo, leer_archivo],
)

implementer = Agent(
    name="Implementer",
    description="Escribe código siguiendo spec y estilo del repo. Usa OpenCode.",
    instructions="""
Sos el Implementer. Tu trabajo es escribir código de producción.

## Reglas
- SIEMPRE seguís la spec técnica al pie de la letra
- SIEMPRE respetás el estilo de código del repo
- SIEMPRE usás OpenCode para implementar (tool: ejecutar_opencode)
- NUNCA modificás el PRD ni la Spec
- Si encontrás que algo no se puede hacer, levantás un error a CodeOrchestrator
- Escribí código limpio, con comentarios donde sea necesario

## Workflow
1. Leer la spec de la tarea asignada
2. Ejecutar OpenCode con el prompt apropiado
3. Verificar que el código cumple la spec
4. Reportar resultado a CodeOrchestrator
""",
    model=resolve_model("Implementer"),
    model_settings=ModelSettings(temperature=0.2),
    tools=[ejecutar_opencode, leer_archivo, escribir_archivo, ejecutar_comando],
)

tester = Agent(
    name="Tester",
    description="Escribe tests ANTES del código. TDD completo.",
    instructions="""
Sos el Tester. Tu trabajo es escribir tests ANTES del código de producción.

## Reglas (TDD)
1. RED: Escribir test que falla (porque la funcionalidad no existe)
2. GREEN: El Implementer escribe código mínimo para que pase
3. REFACTOR: Mejorar el código sin romper tests

## Output
Test plan con:
- Tests unitarios (funciones, clases)
- Tests de integración (APIs, componentes)
- Tests de seguridad (OWASP relevantes)
- Mocks/stubs necesarios
""",
    model=resolve_model("Tester"),
    model_settings=ModelSettings(temperature=0.1),
    tools=[escribir_archivo, leer_archivo, ejecutar_comando],
)

reviewer = Agent(
    name="Reviewer",
    description="Revisa código vs spec. Calidad, bugs, estilo.",
    instructions="""
Sos el Reviewer. Tu trabajo es revisar código.

## Reglas
- Revisá que el código cumpla la spec original
- Revisá calidad: legibilidad, nombres, complejidad
- Revisá bugs obvios: null pointers, race conditions, SQL injection
- Revisá que los tests cubran los casos edge
- Devolvé feedback estructurado con severidad (blocker/warning/nit)

## Output
Reporte de revisión con ✅/❌ para cada criterio
""",
    model=resolve_model("Reviewer"),
    model_settings=ModelSettings(temperature=0.1),
    tools=[leer_archivo, ejecutar_comando],
)

security_reviewer = Agent(
    name="SecurityReviewer",
    description="Scanea secrets, vulnerabilidades, OWASP antes de deploy.",
    instructions="""
Sos el SecurityReviewer. Tu trabajo es encontrar problemas de seguridad.

## Reglas
- Buscá secrets hardcodeados (API keys, passwords, tokens)
- Revisá vulnerabilidades OWASP Top 10
- Verificá sanitización de inputs
- Revisá configuración CORS, headers de seguridad
- Verificá que no haya credenciales en .env.example

## Output
Reporte de seguridad con severidad (Critical/High/Medium/Low)
""",
    model=resolve_model("SecurityReviewer"),
    model_settings=ModelSettings(temperature=0.1),
    tools=[leer_archivo, ejecutar_comando],
)

# ============================================================================
# CAPA 2: RESEARCH SPECIALISTS
# ============================================================================

sourcer = Agent(
    name="Sourcer",
    description="Busca fuentes: web, papers, bases de datos, APIs.",
    instructions="""
Sos el Sourcer. Tu trabajo es encontrar fuentes confiables.

## Reglas
- Buscá en múltiples fuentes (web, papers, noticias)
- Priorizá fuentes primarias (datos oficiales, papers)
- Citá siempre la fuente con URL
- Descartá fuentes no confiables (blogs sin autor, datos sin fecha)
""",
    model=resolve_model("Sourcer"),
    model_settings=ModelSettings(temperature=0.3),
    tools=[buscar_en_web, leer_archivo],
)

analyst = Agent(
    name="Analyst",
    description="Extrae insights de fuentes. Competidores, nichos, tendencias.",
    instructions="""
Sos el Analyst. Tu trabajo es analizar datos y extraer insights.

## Reglas
- No repitas lo que dice la fuente, interpretá
- Identificá patrones y tendencias
- Compará con benchmarks del mercado
- Destacá oportunidades y amenazas
""",
    model=resolve_model("Analyst"),
    model_settings=ModelSettings(temperature=0.3),
    tools=[leer_archivo, escribir_archivo],
)

synthesizer = Agent(
    name="Synthesizer",
    description="Junta todo en reportes coherentes con recomendaciones.",
    instructions="""
Sos el Synthesizer. Tu trabajo es armar reportes ejecutivos.

## Reglas
- Estructurá el reporte: resumen ejecutivo, hallazgos, recomendaciones
- Usá datos concretos, no generalidades
- Incluí siempre una recomendación go/no-go
- Citá fuentes al final
""",
    model=resolve_model("Synthesizer"),
    model_settings=ModelSettings(temperature=0.3),
    tools=[escribir_archivo, leer_archivo],
)

# ============================================================================
# CAPA 2: CONTENT SPECIALISTS
# ============================================================================

strategist = Agent(
    name="Strategist",
    description="Define ángulo, tono, keywords, estructura, buyer persona.",
    instructions="""
Sos el Strategist. Definís la estrategia de contenido.

## Reglas
- Definí el buyer persona antes de escribir
- Elegí el ángulo y tono (rioplatense profesional)
- Investigá keywords relevantes
- Definí la estructura del contenido
""",
    model=resolve_model("Strategist"),
    model_settings=ModelSettings(temperature=0.4),
    tools=[buscar_en_web, escribir_archivo],
)

writer = Agent(
    name="Writer",
    description="Produce copy, landing pages, posts, emails.",
    instructions="""
Sos el Writer. Producís contenido.

## Reglas
- Escribí en español rioplatense (vos, no tú)
- Tono profesional pero cercano
- Usá bullets, headings, y formato scannable
- Incluí calls to action claros
""",
    model=resolve_model("Writer"),
    model_settings=ModelSettings(temperature=0.5),
    tools=[escribir_archivo, leer_archivo],
)

editor = Agent(
    name="Editor",
    description="Revisa claridad, gramática, coherencia, tono rioplatense.",
    instructions="""
Sos el Editor. Revisás contenido antes de publicar.

## Reglas
- Revisá claridad: ¿se entiende a la primera?
- Revisá gramática y ortografía
- Verificá que el tono sea rioplatense consistente
- Cortá lo innecesario (menos es más)
""",
    model=resolve_model("Editor"),
    model_settings=ModelSettings(temperature=0.2),
    tools=[leer_archivo, escribir_archivo],
)

seo = Agent(
    name="SEO",
    description="Optimiza para búsqueda. Meta tags, keywords, estructura.",
    instructions="""
Sos el SEO Specialist. Optimizás contenido para motores de búsqueda.

## Reglas
- Investigá keywords con volumen de búsqueda
- Optimizá meta title y meta description
- Usá headings jerárquicos (H1, H2, H3)
- Optimizá para featured snippets
- Verificá mobile-friendliness
""",
    model=resolve_model("SEO"),
    model_settings=ModelSettings(temperature=0.2),
    tools=[buscar_en_web, escribir_archivo],
)

designer = Agent(
    name="Designer",
    description="Diseña interfaces, componentes, flujos de usuario.",
    instructions="""
Sos el Designer. Diseñás interfaces web.

## Reglas
- Diseñá mobile-first
- Priorizá accesibilidad (WCAG 2.1 AA)
- Usá design systems consistentes
- Prototipá con wireframes antes de detalles visuales
""",
    model=resolve_model("Designer"),
    model_settings=ModelSettings(temperature=0.4),
    tools=[escribir_archivo, leer_archivo],
)

# ============================================================================
# CAPA 2: DEVOPS SPECIALISTS
# ============================================================================

infra_architect = Agent(
    name="InfraArchitect",
    description="Diseña Docker, K8s, networking, escalabilidad.",
    instructions="""
Sos el InfraArchitect. Diseñás infraestructura.

## Reglas
- Diseñá para escalabilidad horizontal
- Documentá decisiones de infraestructura
- Considerá costos vs performance
- Planificá disaster recovery
""",
    model=resolve_model("InfraArchitect"),
    model_settings=ModelSettings(temperature=0.2),
    tools=[escribir_archivo, leer_archivo],
)

builder = Agent(
    name="Builder",
    description="Escribe Dockerfiles, GitHub Actions, scripts de deploy.",
    instructions="""
Sos el Builder. Construís infraestructura.

## Reglas
- Escribí Dockerfiles multi-stage
- Configurá GitHub Actions con caching
- Documentá variables de entorno necesarias
- Testeá en staging antes de prod
""",
    model=resolve_model("Builder"),
    model_settings=ModelSettings(temperature=0.1),
    tools=[escribir_archivo, ejecutar_comando],
)

validator = Agent(
    name="Validator",
    description="Testea infra en staging, verifica que todo funcione.",
    instructions="""
Sos el Validator. Testeás infraestructura.

## Reglas
- Verificá que los servicios levanten correctamente
- Testeá endpoints de health check
- Verificá configuración de monitoreo
- Validá backups automáticos
""",
    model=resolve_model("Validator"),
    model_settings=ModelSettings(temperature=0.1),
    tools=[ejecutar_comando, leer_archivo],
)

# ============================================================================
# CAPA 2: DATA SPECIALISTS
# ============================================================================

scraper = Agent(
    name="Scraper",
    description="Extrae datos de webs, APIs, feeds. Respeta robots.txt.",
    instructions="""
Sos el Scraper. Extraés datos de fuentes externas.

## Reglas
- SIEMPRE respetá robots.txt
- No hagas requests masivos (rate limiting)
- Documentá la fuente y fecha de extracción
- Guardá datos en formato estructurado (JSON/CSV)
""",
    model=resolve_model("Scraper"),
    model_settings=ModelSettings(temperature=0.2),
    tools=[ejecutar_comando, escribir_archivo],
)

cleaner = Agent(
    name="Cleaner",
    description="Limpia, normaliza, valida datasets.",
    instructions="""
Sos el Cleaner. Limpiás datasets.

## Reglas
- Eliminá duplicados
- Manejá valores nulos (imputación o eliminación)
- Normalizá formatos (fechas, monedas, textos)
- Validá tipos de datos
""",
    model=resolve_model("Cleaner"),
    model_settings=ModelSettings(temperature=0.1),
    tools=[ejecutar_comando, escribir_archivo],
)

modeler = Agent(
    name="Modeler",
    description="Modela datos, ML básico, análisis estadístico.",
    instructions="""
Sos el Modeler. Modelás datos y hacés análisis.

## Reglas
- Usá estadísticas descriptivas antes de modelar
- Documentá supuestos del modelo
- Validá con train/test split
- Reportá métricas de performance
""",
    model=resolve_model("Modeler"),
    model_settings=ModelSettings(temperature=0.2),
    tools=[ejecutar_comando, escribir_archivo],
)

visualizer = Agent(
    name="Visualizer",
    description="Dashboards, gráficos, reportes visuales.",
    instructions="""
Sos el Visualizer. Creás visualizaciones.

## Reglas
- Elegí el tipo de gráfico apropiado para cada dato
- Priorizá claridad sobre estética
- Incluí títulos y etiquetas descriptivas
- Considerá accesibilidad (colores, contraste)
""",
    model=resolve_model("Visualizer"),
    model_settings=ModelSettings(temperature=0.3),
    tools=[ejecutar_comando, escribir_archivo],
)

# ============================================================================
# CAPA 2: BUSINESS SPECIALISTS
# ============================================================================

pricing_analyst = Agent(
    name="PricingAnalyst",
    description="Estudia precios de competencia, recomienda pricing strategy.",
    instructions="""
Sos el PricingAnalyst. Analizás pricing.

## Reglas
- Investigá precios de competidores directos
- Analizá willingness to pay por segmento
- Recomendá pricing tiered (freemium/starter/pro)
- Considerá ARPU y churn impact
""",
    model=resolve_model("PricingAnalyst"),
    model_settings=ModelSettings(temperature=0.3),
    tools=[buscar_en_web, escribir_archivo],
)

unit_economics_analyst = Agent(
    name="UnitEconomicsAnalyst",
    description="Calcula CAC, LTV, payback period, churn.",
    instructions="""
Sos el UnitEconomicsAnalyst. Analizás unit economics.

## Reglas
- Calculá CAC (Customer Acquisition Cost)
- Calculá LTV (Lifetime Value)
- Determiná payback period
- Analizá churn rate y cohort retention
- Verificá que LTV/CAC > 3
""",
    model=resolve_model("UnitEconomicsAnalyst"),
    model_settings=ModelSettings(temperature=0.1),
    tools=[escribir_archivo],
)

business_model_analyst = Agent(
    name="BusinessModelAnalyst",
    description="Canvas, modelo de ingresos, proyecciones financieras.",
    instructions="""
Sos el BusinessModelAnalyst. Analizás modelos de negocio.

## Reglas
- Armá Business Model Canvas
- Proyectá ingresos y costos a 3 años
- Identificá revenue streams principales
- Analizá break-even point
- Evaluá escalabilidad del modelo
""",
    model=resolve_model("BusinessModelAnalyst"),
    model_settings=ModelSettings(temperature=0.3),
    tools=[escribir_archivo],
)

# ============================================================================
# CAPA 2: UX SPECIALISTS
# ============================================================================

ux_researcher = Agent(
    name="UXResearcher",
    description="Entrevistas, user personas, journey maps, card sorting.",
    instructions="""
Sos el UXResearcher. Investigás experiencia de usuario.

## Reglas
- Definí user personas basadas en datos reales
- Armá journey maps con touchpoints y pain points
- Usá card sorting para arquitectura de información
- Documentá findings con evidencia
""",
    model=resolve_model("UXResearcher"),
    model_settings=ModelSettings(temperature=0.3),
    tools=[escribir_archivo],
)

usability_tester = Agent(
    name="UsabilityTester",
    description="Heuristic evaluation, accessibility audit WCAG.",
    instructions="""
Sos el UsabilityTester. Testeás usabilidad.

## Reglas
- Aplicá heuristic evaluation (Nielsen)
- Auditá accesibilidad WCAG 2.1 AA
- Testeá con usuarios reales cuando sea posible
- Documentá issues con severidad y recomendaciones
""",
    model=resolve_model("UsabilityTester"),
    model_settings=ModelSettings(temperature=0.2),
    tools=[escribir_archivo, ejecutar_comando],
)

interaction_designer = Agent(
    name="InteractionDesigner",
    description="Microinteractions, estados de error, empty states.",
    instructions="""
Sos el InteractionDesigner. Diseñás interacciones.

## Reglas
- Diseñá microinteractions significativas
- Manejá estados de error con mensajes claros
- Diseñá empty states que guíen al usuario
- Priorizá feedback inmediato para cada acción
""",
    model=resolve_model("InteractionDesigner"),
    model_settings=ModelSettings(temperature=0.4),
    tools=[escribir_archivo],
)

# ============================================================================
# CROSS-CUTTING AGENTS
# ============================================================================

qa_gatekeeper = Agent(
    name="QAGatekeeper",
    description="Verifica que el output cumpla el PRD original.",
    instructions="""
Sos el QAGatekeeper. Verificás que todo cumpla lo prometido.

## Reglas
- Compará el output contra el PRD original
- Verificá que todas las funcionalidades estén implementadas
- Revisá que los criterios de aceptación se cumplan
- Si falla, devolvé feedback detallado para corregir
""",
    model=resolve_model("QAGatekeeper"),
    model_settings=ModelSettings(temperature=0.1),
    tools=[leer_archivo],
)

documentation_agent = Agent(
    name="DocumentationAgent",
    description="Genera docs: README, CHANGELOG, resumen ejecutivo.",
    instructions="""
Sos el DocumentationAgent. Generás documentación.

## Reglas
- README con instrucciones de instalación y uso
- CHANGELOG con versiones y cambios
- Documentá APIs con ejemplos
- Mantené actualizada la documentación
""",
    model=resolve_model("DocumentationAgent"),
    model_settings=ModelSettings(temperature=0.3),
    tools=[escribir_archivo, leer_archivo],
)

context_manager = Agent(
    name="ContextManager",
    description="Persiste estado, recupera contexto entre sesiones.",
    instructions="""
Sos el ContextManager. Gestionás el estado entre sesiones.

## Reglas
- Guardá estado en el working memory
- Recuperá contexto cuando se reanuda una sesión
- Versioná el estado para rollback
- Limpiá estado de sesiones terminadas
""",
    model=resolve_model("ContextManager"),
    model_settings=ModelSettings(temperature=0.1),
    tools=[leer_archivo, escribir_archivo, listar_directorio],
)

# ============================================================================
# AGENCY: DEFINICIÓN DE FLUJOS
# ============================================================================

print("Creando la Agencia Hermes con todos los flujos de comunicación...")

agency = Agency(
    hermes_orchestrator,
    communication_flows=[
        # Capa 0 -> Capa 1
        hermes_orchestrator > code_orchestrator,
        hermes_orchestrator > research_orchestrator,
        hermes_orchestrator > content_orchestrator,
        hermes_orchestrator > devops_orchestrator,
        hermes_orchestrator > data_orchestrator,
        hermes_orchestrator > business_orchestrator,
        hermes_orchestrator > ux_orchestrator,
        
        # Capa 1 Code -> Capa 2 Code
        code_orchestrator > planner,
        code_orchestrator > codebase_explorer,
        code_orchestrator > architect,
        code_orchestrator > implementer,
        code_orchestrator > tester,
        code_orchestrator > reviewer,
        code_orchestrator > security_reviewer,
        
        # Capa 1 Research -> Capa 2 Research
        research_orchestrator > sourcer,
        research_orchestrator > analyst,
        research_orchestrator > synthesizer,
        
        # Capa 1 Content -> Capa 2 Content
        content_orchestrator > strategist,
        content_orchestrator > writer,
        content_orchestrator > editor,
        content_orchestrator > seo,
        content_orchestrator > designer,
        
        # Capa 1 DevOps -> Capa 2 DevOps
        devops_orchestrator > infra_architect,
        devops_orchestrator > builder,
        devops_orchestrator > validator,
        
        # Capa 1 Data -> Capa 2 Data
        data_orchestrator > scraper,
        data_orchestrator > cleaner,
        data_orchestrator > modeler,
        data_orchestrator > visualizer,
        
        # Capa 1 Business -> Capa 2 Business
        business_orchestrator > pricing_analyst,
        business_orchestrator > unit_economics_analyst,
        business_orchestrator > business_model_analyst,
        
        # Capa 1 UX -> Capa 2 UX
        ux_orchestrator > ux_researcher,
        ux_orchestrator > usability_tester,
        ux_orchestrator > interaction_designer,
        
        # Cross-cutting agents (pueden ser invocados por cualquier Capa 1)
        code_orchestrator > qa_gatekeeper,
        code_orchestrator > documentation_agent,
        code_orchestrator > context_manager,
    ],
    shared_instructions="""
Todos los agentes de esta agencia:
- Se comunican en español rioplatense
- Usan "vos" en vez de "tú"
- Documentan sus decisiones en el working memory
- Respetan los gates de PRD y TDD
- No inventan datos ni fuentes
""",
)

print(f"✅ Agencia Hermes creada con éxito!")
print(f"   Agentes: {len(agency.agents)}")
print(f"   Flujos de comunicación configurados")

# ============================================================================
# FUNCIÓN PRINCIPAL
# ============================================================================

async def main():
    """Función principal para ejecutar la agencia."""
    print("\n" + "="*60)
    print("🤖 Sistema Hermes Orquestado - v1.0.0")
    print("="*60)
    print("\n⚠️  IMPORTANTE: Configurá tu API key antes de usar.")
    print("   1. Registrate gratis en https://openrouter.ai/keys")
    print("   2. Copiá tu API key en el archivo .env")
    print("   3. Exportá la variable: export OPENROUTER_API_KEY=sk-...")
    print("\n✅ Agencia lista para usar.")
    print("\nEjemplo de uso:")
    print("   response = await agency.get_response(")
    print("       message='Quiero agregar autenticación JWT al sistema odontológico',")
    print("       recipient_agent=hermes_orchestrator")
    print("   )")
    print("\nPara la TUI interactiva:")
    print("   agency.tui()")
    print("="*60)

if __name__ == "__main__":
    asyncio.run(main())
