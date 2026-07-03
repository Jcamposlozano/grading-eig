---
description: Sesión de planeación (explorar → preguntar → proponer plan → esperar OK), sin tocar código de producción
argument-hint: [tema o alcance a planear]
allowed-tools: Read, Glob, Grep, Task, Write, Edit
---

Estás en una **sesión de planeación** para evolucionar el calificador `grading-eig`.

**Regla #1:** NO escribas ni modifiques código de producción. Solo puedes crear/editar
documentos de plan (`docs/*.md`) y configuración de `.claude/`. Todo lo demás es propuesta
escrita que el usuario debe aprobar antes de implementar.

Trabaja en este orden:

1. **Explorar.** Audita el repo relacionado con: $ARGUMENTS
   - Usa subagentes `Explore` en paralelo si el alcance es amplio.
   - No asumas: verifica en el código qué se extrae/maneja hoy antes de proponer.
2. **Preguntar.** Párate y muestra el mapa del estado actual + tus dudas. Usa
   `AskUserQuestion` para las decisiones que cambian el diseño (no inventes defaults
   sobre intención del usuario).
3. **Proponer.** Redacta/actualiza el plan correspondiente (por defecto
   `docs/PLAN_ESCALABILIDAD.md`), alineado con la arquitectura hexagonal y las
   convenciones del template (ver `CLAUDE.md`). Sé incremental (sin big-bang).
4. **Esperar OK.** No implementes nada hasta que el usuario apruebe el plan.

Contexto base obligatorio: lee `CLAUDE.md` y `docs/PLAN_ESCALABILIDAD.md` antes de empezar.
