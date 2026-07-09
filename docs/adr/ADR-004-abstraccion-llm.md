# ADR-004 — Capa propia de abstracción LLM, sin framework

Fecha: 2026-07-06 · Estado: **Aceptado**

## Contexto
Requisito: usar Claude/ChatGPT/Gemini/Ollama indistintamente sin tocar el resto del sistema.

## Alternativas
1. SDK de un proveedor directo en el código: lock-in, viola el requisito.
2. Framework (LangChain/LlamaIndex): resuelve la abstracción pero importa un ecosistema
   grande, volátil y con abstracciones que filtran, para un uso mínimo (completar con JSON estructurado).
3. LiteLLM (proxy/lib de compatibilidad): opción intermedia razonable; una dependencia
   que traduce a formato OpenAI. Menos control sobre errores/costos por tarea.
4. **Interfaz propia mínima (elegida):** `LLMProvider` (Protocol) + un adaptador de ~50-100
   líneas por proveedor + registro de consumo propio.

## Decisión
Interfaz propia. La superficie necesaria es tan pequeña que un framework cuesta más de
lo que da. LiteLLM queda anotado como reemplazo interno aceptable de los adaptadores si
su mantenimiento se vuelve tedioso — el resto del sistema no notaría el cambio (esa es
la prueba de que la abstracción está bien puesta).

## Consecuencias
- (+) Cero lock-in, control total de costos, privacidad verificable (un solo punto de salida de datos).
- (−) Mantener adaptadores propios ante cambios de APIs de proveedores.
- Pendiente al implementar: verificar en documentación oficial las políticas de retención
  de datos del proveedor elegido por defecto. No asumir.
