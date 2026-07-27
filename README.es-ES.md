<div align="center">

<picture>
  <source media="(prefers-color-scheme: light)" srcset="assets/orb_light.png">
  <img alt="doxa" src="assets/orb_dark.png" width="200">
</picture>

# doxa

**oráculo de creencias** &nbsp;&middot;&nbsp; conocimiento basado en citas para agentes &nbsp;&middot;&nbsp; sin cita, no hay afirmación

<p>
  <a href="https://x.com/advait_jayant"><img src="https://img.shields.io/twitter/follow/advait_jayant?style=social" alt="Follow @advait_jayant"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-blue.svg" alt="License: MIT"></a>
  <img src="https://img.shields.io/badge/Python-3.10%2B-blue.svg" alt="Python 3.10+">
</p>

</div>

---

Convierte las fuentes en las que confías en una base de creencias que puedes consultar, donde cada respuesta está anclada a una **cita textual**, para que el modelo no pueda inventar cosas.

La mayoría de las herramientas de "chat con tus notas" permiten que un LLM parafrasee tus fuentes e invente el resto discretamente. doxa no lo hace. Extrae ensayos, PDFs, páginas web y transcripciones en dos registros vinculados: una **creencia** concisa y la **cita exacta** que la fundamenta. Tú consultas las creencias; cada respuesta rastrea hasta el texto real de la fuente. Sin cita, no hay afirmación.

- **Fundamentado textualmente** — cada creencia enlaza a una cita exacta de la fuente; las citas nunca son generadas por el modelo.
- **Bases de conocimiento personalizadas listas para agentes** — instálalo como una habilidad para Claude Code, Codex, Hermes, OpenCLAW u otro entorno compatible con CLI.
- **Local y portable** — una fuente de verdad en JSONL simple que puedes leer, comparar (diff) y re-indexar.
- **Cualquier lente, cualquier modelo** — extrae una fuente a través de tu perspectiva, con codex-cli / claude-cli (sin clave de API) o OpenAI / Fireworks / Anthropic.
- **Recuperación basada en citas** — la búsqueda por palabras clave indexa los documentos de creencias y de citas, y luego pliega los aciertos de las citas hacia las creencias vinculadas.
- **Preferencias de dominio** — pesos de dominio pequeños (0-10) orientan las etiquetas de extracción y potencian la recuperación sin cambiar el esquema JSONL. Los alias mantienen útiles las etiquetas simples más antiguas.
- **Palabra clave → semántica → híbrida** — funciona sin configuración; añade embeddings cuando los necesites.

**Para agentes de IA:** comienza con [AGENTS.md](AGENTS.md); instálalo como una habilidad de entorno vía [skill/SKILL.md](skill/SKILL.md).

---

## Inicio rápido

```bash
python -m pip install -e .
doxa                  # banner + aterrizaje de inicio rápido
doxa guide            # guía completa, en cualquier momento
doxa demo             # pruébalo con datos de dominio público incluidos
doxa packs install startup-wisdom   # opcional: una base ya preparada para fundadores/producto/crecimiento
doxa query "self-reliance and conformity" --top 2
```

¿Eres nuevo en la CLI? Simplemente ejecuta `doxa` (o `doxa guide`). `doxa status` muestra el estado actual: tu configuración, ubicación de datos y conteos de creencias/citas. Cada comando acepta `-h` para ver sus opciones.

`doxa banner` usa por defecto `--color auto`: los acentos ANSI aparecen en una terminal interactiva, mientras que las tuberías (pipes), capturas y ejecuciones de prueba permanecen simples. Usa `--color always` o `--color never` para anularlo.

Sin un archivo `doxa.yaml` en el directorio actual, `doxa query` utiliza los datos de demostración de dominio público incluidos de "Self-Reliance" de Emerson, "Apology" de Platón y el "Federalist No. 10" de Madison.

Ejemplo:

```text
1. Personhood requires resisting social conformity.
   stance=supports conviction=0.91 score=13.1877
   source=Self-Reliance / Ralph Waldo Emerson / 1841
   quote="Ralph Waldo Emerson: Whoso would be a man must be a nonconformist."
2. Self-trust is a necessary starting point for thought and action.
   stance=supports conviction=0.93 score=11.6399
   source=Self-Reliance / Ralph Waldo Emerson / 1841
   quote="Ralph Waldo Emerson: Trust thyself: every heart vibrates to that iron string."
```

La búsqueda por palabras clave funciona sin clave de API, base de datos, modelo de embeddings o red.

> **¿Quieres valor instantáneo?** `doxa packs install startup-wisdom` instala una base opcional y ya extraída de ~14k creencias de fundadores/producto/crecimiento de Lenny's Podcast, View From The Top, Paul Graham y Y Combinator; cada una anclada a una cita textual + enlace a la fuente. Explora los paquetes con `doxa packs list`.

---

## Documentación

- [Configuración](docs/configuration.md) · [Proveedores](docs/providers.md) · [Ingesta](docs/ingestion.md)
- [Recuperación](docs/retrieval.md) · [Escribir una lente](docs/writing-a-lens.md) · [Esquema](docs/schema.md) · [Arquitectura](docs/architecture.md) · [Modos de presentación](docs/presentation.md)
- [Habilidad de agente](docs/skill.md) · [AGENTS.md](AGENTS.md) · [skill/SKILL.md](skill/SKILL.md)
- [Galería de ejemplos de configuración](examples/README.md) -- plantillas de `doxa.yaml` listas para copiar
- [Ejemplos de Preguntas y Respuestas](docs/examples-qa.md) -- respuestas fundamentadas en la base de demo

---

## Ejemplos de preguntas y respuestas

Un recorrido por respuestas fundamentadas en la demo incluida (Emerson, Platón, Madison) — incluyendo una tensión socrática real que doxa hace emerger en lugar de aplanar — se encuentra en [docs/examples-qa.md](docs/examples-qa.md). O simplemente ejecútalo:

```bash
doxa demo
doxa query "Should I trust my own judgment over the crowd?"
```

---

## Modos de presentación (opcional)

doxa devuelve evidencia; el agente que la lee escribe la respuesta en prosa. Un **modo de presentación** es una voz opcional para ese paso final. El predeterminado es `plain` (salida sin cambios). El modo opcional insignia es `hawking`, destilado de cómo Stephen Hawking presentaba evidencia en los dos primeros capítulos de *A Brief History of Time*: abrir con la pregunta antigua en lugar del aparato, dejar que la evidencia llegue como una procesión de mentes, decir lo más grande en la frase más sencilla, mantener intacta la extrañeza genuina y convertir la respuesta en una pregunta sobre lo que podemos saber.

```bash
doxa present --list                 # listar modos
doxa present hawking                # leer la directiva de composición
doxa query "did time have a beginning?" --answer --present hawking
```

Con un modo distinto de `plain`, `doxa query` imprime un bloque `=== doxa presentation directive ===` antes de la evidencia; un agente lo lee y compone con esa voz. El modo solo cambia la voz y la forma, nunca flexibiliza la regla de fundamentación textual, por lo que la respuesta se sigue construyendo únicamente a partir de las creencias y citas devueltas. Con `--json`, un modo no-plain envuelve la salida como `{"presentation": {...}, "results": [...]}`; `plain` permanece como una lista simple. Haz que un modo sea persistente en `doxa.yaml` con `presentation.default`, o añade el tuyo registrando un `PresentationProfile` en `doxa/present.py`. Consulta [docs/presentation.md](docs/presentation.md).

---

## Por qué existe doxa

La fluidez es donde se esconden las alucinaciones: un resumidor puede comprimir, exagerar, fusionar afirmaciones o inventar palabras que nunca estuvieron en la fuente. doxa sacrifica un poco de fluidez a cambio de una garantía que puedes auditar.

`doxa` adopta un enfoque más estricto:

- Una `Belief` (creencia) es una afirmación, postura, valor o razón destilada.
- Una `Quote` (cita) es una subcadena exacta de la fuente que fundamenta una o más creencias.
- Después de la extracción, doxa verifica cada cita propuesta contra el texto original de la fuente mediante una coincidencia textual normalizada en espacios en blanco.
- Las citas que no están realmente presentes se descartan antes de entrar en el almacén.
- Las creencias sin enlaces a citas supervivientes también se descartan.

La otra diferencia es la lente. Tú defines qué tipo de creencia quieres extraer. Una lente de estrategia, una lente legal, una lente filosófica y una lente de producto pueden leer la misma fuente y producir bases de creencias diferentes.

---

## doxa vs. una app de RAG

<details>
<summary>Versión corta: es tubería de RAG envuelta alrededor de un grafo curado de creencias + citas. Expande para la respuesta completa.</summary>

Bajo el capó, doxa *es* tubería de RAG: híbrido BM25 + pgvector sobre un almacén embebido. La diferencia es qué hay en el índice y qué sucede a su alrededor.

Una app de RAG normal indexa fragmentos de documentos crudos: preguntas, extrae los pasajes más similares y el modelo los resume. La unidad de recuperación es un trozo del documento de alguien.

El índice de doxa no es texto crudo. Son **creencias** autoradas — cada una una postura destilada extraída fuera de línea de la fuente, que lleva su razonamiento, postura y convicción, con las **citas textuales que la generaron** adjuntas y verificadas mediante grep contra el original. La unidad de recuperación es una opinión destilada más sus comprobantes, no un fragmento de transcripción. Ese paso de destilación es la parte que una app de RAG se salta.

De ahí se derivan tres cosas que una app de RAG vainilla no tiene:

- **Honestidad tipada.** Cada creencia lleva cuánto confiar en ella (una convicción y espacio para un estado epistémico). doxa se niega a emitir un número falso de "87% verdadero"; te dice qué afirmaciones son fundamentales y cuáles son simples impresiones.
- **Atribución, no adjudicación.** La cita es el *objeto almacenado*, vinculado y textual ("X dijo literalmente esto"). Nunca fabrica una cita, que es el modo de fallo que sufre el RAG cuando cita un fragmento que no respalda la frase generada.
- **Un punto de vista, no un volcado de corpus.** Cada creencia vive en una lente, por lo que la recuperación devuelve una cosmovisión. El RAG responde a "¿qué dicen los documentos sobre X?"; doxa responde a "¿cuál es la posición sobre X, y aquí está quien dijo lo que fundamenta esa posición?".

La frase honesta: doxa es tubería de RAG envuelta alrededor de un grafo curado de creencias y citas con honestidad epistémica tipada, consultado como un punto de vista en lugar de una búsqueda de documentos. El recuperador nunca fue la ventaja competitiva; el modelo de datos y la disciplina sobre él lo son.

</details>

---

## Cómo funciona

```text
 texto / PDF / URL / YouTube / notas
                |
                v
        mine [provider + lens]
                |
                v
      JSON beliefs + verbatim quotes
                |
                v
 JSONL source of truth (+ optional pgvector index)
                |
                v
 keyword / semantic / hybrid retrieve
                |
                v
 grounded answer with linked quotes
```

JSONL es la fuente de verdad durable. Postgres/pgvector es opcional y puede reconstruirse desde JSONL en cualquier momento.

---

## Instalación

El núcleo es intencionalmente pequeño (configuración, demo, consulta por palabra clave, evaluación, ingesta de texto/URL):

```bash
python -m pip install -e .           # core
python -m pip install -e ".[all]"    # todas las integraciones opcionales
```

Instala solo los extras que necesites: `embeddings` (vectores semánticos), `postgres` (pgvector), `pdf`, `youtube`, `openai`, `anthropic`, ej. `pip install -e ".[pdf,youtube]"`. Matriz completa de extras + configuración de desarrollo: [docs/configuration.md](docs/configuration.md).

---

## Configuración

```bash
doxa init            # interactivo: proveedor, modelo, lente -> escribe doxa.yaml
doxa status          # config, dir de datos, conteos de creencias/citas, proveedor, semántica
```

**No inventes tu primera lente** — una lente es la pregunta que doxa hace mientras lee, y "cuál elegir" no es obvio, por lo que doxa incluye una librería opinada:

```bash
doxa lenses list                                  # founder-strategy, investment-memo, ...
doxa init --lens-template founder-strategy        # crea una config desde una plantilla
doxa lenses add my-lens --from founder-strategy   # bifurca una y hazla tuya
```

Integradas: `durable-beliefs`, `founder-strategy`, `investment-memo`, `technical-design`, `research-literature`, `policy-analysis`, `personal-principles`, `customer-discovery`. `doxa init` también es automatizable (`--yes --provider ... --model ...`), y los pesos de dominio ajustan la recuperación (`doxa domains set technical 8`). Opciones completas: [docs/configuration.md](docs/configuration.md) · [escribir una lente](docs/writing-a-lens.md).

---

## Proveedores

| Proveedor | ¿Clave? | Ideal para |
| --- | --- | --- |
| `codex-cli` / `claude-cli` | No (reutiliza tu login de CLI) | configuración interactiva local |
| `openai` | `OPENAI_API_KEY` | extracción vía API |
| `openai-compatible` / `fireworks` | usualmente una clave | modelos personalizados / de pesos abiertos |
| `anthropic` | `ANTHROPIC_API_KEY` | extracción vía API |

Configuración + ejemplo de Fireworks: [docs/providers.md](docs/providers.md).

---

## Ingesta de fuentes

```bash
doxa ingest ./essay.md ./paper.pdf            # archivos (funcionan globs de shell)
doxa ingest https://example.com/article       # URL
doxa ingest "https://youtube.com/watch?v=..." # video (transcripción yt-dlp)
pbpaste | doxa ingest - --title "Notes"       # stdin
```

| Fuente | Requisito |
| --- | --- |
| texto / stdin / URL | core |
| PDF | `doxa[pdf]` |
| YouTube | `doxa[youtube]` |

Las citas que no sean textuales en la fuente se descartan. La re-ingesta se omite por defecto (`--reingest` para reemplazar); `doxa sources list` / `doxa sources remove <id>` gestionan la base. Guía completa: [docs/ingestion.md](docs/ingestion.md).

### Extractores web (enchufables)

No está atado a un solo scraper; elige por ingesta con `--via`, o define `sources.fetcher`:

| Extractor | ¿Clave? | Qué hace |
| --- | --- | --- |
| `requests` | No | HTTP simple + extracción de HTML (predeterminado) |
| `jina` | opcional | markdown limpio, gratis |
| `firecrawl` | `FIRECRAWL_API_KEY` | API de scraping |
| `brightdata` | tokens | Web Unlocker |
| `command` | -- | ejecuta CUALQUIER herramienta / puente MCP |
| `claude` / `codex` / `hermes` | -- | un agente de codificación navega por ti |

```bash
doxa ingest <url> --via jina                          # gratis, markdown limpio
doxa ingest <url> --via hermes --mode browser         # renderiza JS, luego markdown
doxa ingest <url> --via codex --mode extract --prompt "name, price as JSON"
```

Los extractores de agentes se ejecutan de forma segura por defecto; añade `--yolo` para omitir confirmaciones en fuentes confiables. El extractor `command` y `register_fetcher()` permiten conectar cualquier otra cosa. Detalles completos: [docs/ingestion.md](docs/ingestion.md).

---

## Consulta (Query)

```bash
doxa query "faction and liberty"            # palabra clave (predeterminado, cero config)
doxa query "examined life" --answer         # resumen de evidencia legible
doxa query "examined life" --json           # salida para máquina
doxa query "..." --top 10 --domain policy   # más resultados, sesgado por tema
```

La búsqueda por palabras clave cubre el texto de la creencia y de la cita (una frase que solo esté en una cita aún encuentra su creencia). Cita solo lo que doxa devuelve. Referencia completa + configuración semántica/híbrida: [docs/retrieval.md](docs/retrieval.md).

---

## Búsqueda semántica (opcional)

```bash
python -m pip install -e ".[embeddings,postgres]"
export DOXA_POSTGRES_DSN=postgresql://...     # luego habilita pgvector: CREATE EXTENSION vector
doxa index
doxa query "political conflict" --search hybrid
```

El modo híbrido fusiona palabras clave + semántica y vuelve a palabras clave si el índice no está disponible. Detalles: [docs/retrieval.md](docs/retrieval.md).

---

## Evaluación de fidelidad

```bash
doxa eval      # verifica que cada cita siga siendo textual y cada creencia esté vinculada (salida !=0 si falla)
doxa doctor    # estado de config, almacenamiento, proveedor y disponibilidad del índice semántico
```

---

## Úsalo como habilidad de agente

doxa incluye una habilidad portable para que un agente llame a la CLI y trate las citas como verdad absoluta:

```bash
doxa skill install --harness claude-code   # o codex / hermes / openclaw / generic
```

Detalles: [docs/skill.md](docs/skill.md) y [AGENTS.md](AGENTS.md).

---

## Lente y esquema

Una **lente** es la pregunta que doxa hace mientras lee (lo estrecho es mejor que lo amplio) — [docs/writing-a-lens.md](docs/writing-a-lens.md). Las creencias y citas son JSONL simple; referencia de campos en [docs/schema.md](docs/schema.md).

---

## FAQ

**¿Evita doxa todas las alucinaciones?**

Evita que citas no textuales entren en el almacén. La interpretación en una creencia aún puede ser demasiado amplia o estrecha, así que mantén las lentes nítidas y ejecuta `doxa eval`.

**¿Necesito Postgres?**

No. La recuperación por palabras clave es puro Python y funciona al instante. Postgres/pgvector es solo para búsqueda semántica e híbrida.

**¿Con qué proveedor debería empezar?**

Usa `codex-cli` si ya usas Codex CLI. Usa `claude-cli` si ya usas Claude Code. Usa OpenAI, Fireworks o Anthropic cuando quieras extracción basada en API en scripts o servicios.

**¿Dónde se guardan mis datos?**

Por defecto, junto a `doxa.yaml` en `data/*.jsonl`. Los proveedores de API reciben los fragmentos de la fuente que ingieres, así que elige proveedores según tu política de datos.

**¿Puedo inspeccionar, actualizar o eliminar lo que he ingerido?**

Sí. `doxa sources list` muestra cada fuente ingerida con sus conteos de creencias/citas; `doxa sources remove <id>` elimina una fuente y sus filas; la re-ingesta reemplaza una fuente con `--reingest`. El almacén también es JSON delimitado por líneas que puedes editar a mano; mantén las cadenas de citas textuales, luego ejecuta `doxa eval` (y `doxa index` si usas búsqueda semántica) para volver a verificar y reconstruir.

---

## Solución de problemas

- **"Config not found"** — ejecuta `doxa init` aquí, o apunta a una con `--config <path>`.
- **"Set OPENAI_API_KEY / ..."** — exporta la clave, o cambia a un proveedor sin clave: `doxa init --provider codex-cli`.
- **"needs the Codex/Claude CLI on PATH"** — instala esa CLI, o elige otro proveedor con `doxa init`.
- **Errores de semántica / `doxa index`** — verifica que `DOXA_POSTGRES_DSN` apunte a un Postgres en ejecución con pgvector habilitado (`CREATE EXTENSION vector` como superusuario/propietario). `doxa status` muestra si la semántica está lista.
- **¿Consultando datos incorrectos?** — sin un `doxa.yaml` presente, doxa usa la base de demo incluida y lo indica en stderr. `doxa status` muestra la config activa y los conteos.
- **Para ver el traceback completo** en un reporte de error: define `DOXA_DEBUG=1` antes del comando.

---

## Nota sobre Platón

`doxa` es griego para creencia, opinión, o aquello que parece ser el caso.

---

## Contribuir

Solo ejemplos de dominio público o explícitamente licenciados. No añadas corpora privados, claves de API, secretos generados o pruebas dependientes de la red. Mantén las dependencias del núcleo mínimas y haz que las integraciones opcionales sean explícitas a través de extras.

El banner de la terminal (`doxa/_assets/banner.txt`) se genera a partir del arte fuente en `assets/` — la marca DOXA es de medio bloque, el orbe del oráculo es braille. Para regenerarlo tras cambiar el arte, ejecuta `python3 tools/build_banner.py` (requiere Pillow).

Ejecuta:

```bash
python -m pytest -q
doxa demo
doxa query "self-reliance and conformity" --search keyword
doxa query "self-reliance and conformity" --search keyword --answer
```

Licenciado bajo la Licencia MIT. Consulta [LICENSE](LICENSE).
