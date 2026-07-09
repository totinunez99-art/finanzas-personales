# Plantilla de caso golden

Pasos para crear un caso (detalle en docs/13 §5):

1. Copiar esta carpeta al destino correcto con nombre `NNN-descripcion-corta`
   (`cases/statements/<banco>/`, `cases/emails/<banco>/<tipo>/`, `cases/scenarios/`,
   `cases/classification/`, `cases/edge/` o `cases/errors/`). El `NNN` no se reutiliza jamás.
2. Colocar el/los input(s) YA ANONIMIZADOS (`golden/tools/anonymize.py` sobre el original).
3. Escribir `expected.json` a mano o verificado a mano línea por línea.
   NUNCA aceptar ciegamente la salida del parser como esperado (test tautológico).
4. Completar `case.yaml`.
5. Correr `golden/tools/verify_no_leaks.py` y revisar visualmente el input.
6. Borrar este README de la copia. PR.
