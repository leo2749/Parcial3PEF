# Motor de recomendaciones eficiente

Sistema de recomendación por **filtrado colaborativo usuario-usuario** (similitud de Jaccard),
desarrollado para la materia Programación Eficiente (Opción 2). El foco del proyecto es la
**eficiencia**: estructuras de datos, algoritmos, caché, concurrencia y procesamiento de
archivos grandes, medidos con benchmarks, profiling y controles automáticos en el CI.

Esta documentación es la **fuente central** de información funcional, técnica y operativa del
sistema. Vive en el mismo repositorio que el código (carpeta `docs/`), se revisa en los mismos
pull requests y se publica automáticamente en GitHub Pages en cada integración a `main`.

## Contenido

| Sección | Qué responde |
|---|---|
| [1. Descripción funcional](funcional.md) | Qué problema resuelve, alcance y requisitos |
| [2. Arquitectura](arquitectura.md) | Módulos, responsabilidades, dependencias y diagrama de componentes |
| [3. Instalación y ejecución](instalacion.md) | Dependencias, configuración y comandos |
| [4. Diseño técnico](diseno.md) | Estructuras de datos, algoritmos y decisiones de implementación |
| [5. API y contratos](api.md) | Endpoints, entradas, salidas, errores y ejemplos |
| [6. Pruebas](pruebas.md) | Estrategia, casos de prueba y resultados |
| [7. Rendimiento](rendimiento.md) | Benchmarks, profiling, complejidad y memoria |
| [8. Seguridad](seguridad.md) | Riesgos, dependencias, política de bloqueo y excepciones |
| [9. Mantenimiento](mantenimiento.md) | Cómo contribuir, correr los controles y arreglar el pipeline |
| [Matriz de controles](calidad/controles.md) | Cada control del CI: herramienta, comando, reporte y criterio |
| [Diseño del pipeline](calidad/pipeline.md) | Etapas, paralelismo y qué pasa cuando algo falla |

## En una línea

```bash
python -m pip install -r requirements-dev.txt && python ci.py
```

Ese comando corre en tu máquina **exactamente los mismos controles** que el CI de GitHub Actions.
Ver [Matriz de controles](calidad/controles.md#como-ejecutar-los-controles-en-local).
