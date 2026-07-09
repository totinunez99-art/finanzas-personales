# ⛔ ZONA NO VERSIONADA — DATOS REALES

Esta carpeta contiene cartolas y correos bancarios ORIGINALES, con datos financieros
y personales reales. Está excluida de git (.gitignore) y así debe permanecer.

- Estructura: `statements/<banco>/<cuenta>/<YYYY-MM>.<ext>` y `emails/<banco>/<tipo>/<fecha>_<n>.eml`
- El mapeo de anonimización (`mapping.json`) también vive aquí y también es secreto.
- Respaldo: SOLO dentro del backup cifrado del sistema (docs/06 §5). Jamás en git,
  jamás en OneDrive sin cifrar.

Si este README es lo único que ves en un clon del repo, es correcto: los originales
solo existen en el PC del dueño.
