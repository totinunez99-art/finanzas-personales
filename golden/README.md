# Golden Dataset

Datos reales anonimizados para pruebas de integración. **Estrategia completa y reglas:
[docs/13-golden-dataset.md](../docs/13-golden-dataset.md)** — leerla antes de tocar esta carpeta.

Reglas no negociables:

1. `originals/` NUNCA entra a git (está en .gitignore). Contiene datos financieros reales.
2. En `cases/` solo entra material anonimizado y verificado (`tools/verify_no_leaks.py` + revisión manual).
3. Un caso mergeado es inmutable: el comportamiento nuevo se prueba con casos nuevos.
4. Todo bug de producción se convierte en caso golden ANTES de corregirse.

Crear un caso nuevo: copiar `cases/_TEMPLATE/`, seguir su README, abrir PR.
