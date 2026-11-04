# Herramienta de documentación

## Elección: MkDocs + Material for MkDocs, en Git y publicada en GitHub Pages

| Criterio | Cómo se cumple |
|---|---|
| Externa al código fuente | Sitio independiente con navegación, búsqueda y modo oscuro; no son comentarios del código |
| Centralizada | Funcional, técnica y operativa en un solo sitio; la referencia de la API se genera desde los docstrings (mkdocstrings) |
| Lugar compartido | Repositorio de GitHub (fuente) + GitHub Pages (sitio publicado) |
| Control de acceso | Permisos del repositorio: integrantes con *Write*, docente con *Read*; `main` protegida |
| Colaboración | Se edita con pull requests: revisión, comentarios por línea e historial de cambios |
| Siempre actualizada | Vive junto al código: el mismo PR que cambia el comportamiento cambia la documentación. El CI rechaza el PR si el sitio no se construye o tiene enlaces rotos |
| Reproducible | `python -m mkdocs serve` muestra en local exactamente lo que se publica |

## Alternativas consideradas

| Herramienta | Por qué no |
|---|---|
| Confluence / SharePoint | Fuera del repositorio: se desactualiza respecto del código y no se puede validar en el CI |
| GitHub Wiki | Repositorio aparte, sin revisión por PR ni validación automática |
| Sphinx | Se usó en el segundo parcial (se conserva en `docs/*.rst`). Escribir en reStructuredText es más costoso; mkdocstrings da la misma autodocumentación desde docstrings |
| GitBook / Read the Docs | Servicio externo adicional; GitHub Pages ya está integrado con el repositorio y con Actions |

## Flujo

```mermaid
flowchart LR
    A["Editar docs/*.md<br/>en una rama"] --> B["Pull request"]
    B --> C["CI: mkdocs --strict<br/>markdownlint · lychee"]
    C --> D["Revisión de otro integrante"]
    D --> E["Merge a main"]
    E --> F["docs.yml publica<br/>en GitHub Pages"]
```

## Comandos

```bash
python -m mkdocs serve             # vista previa con recarga automática
python -m mkdocs build --strict    # lo mismo que valida el CI
python ci.py docs                  # build + markdownlint + lychee
```
