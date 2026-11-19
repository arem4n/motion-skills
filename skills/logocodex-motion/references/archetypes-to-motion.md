# Arquetipos → personalidad de movimiento

Fuente: los 12 arquetipos de Mark & Pearson del manual LogocodeX™ (motivación, temor, estética) más los dos
arquetipos junguianos que aparecen en el caso AreMan (Ancestro/Anciano Sabio y Guardián del Umbral). Los valores
viven en `assets/motion-tokens.json`; este archivo explica cómo usarlos.

## Cómo leer un token

| Campo | Significado | Cómo se usa |
|---|---|---|
| `tempo` | multiplicador de duraciones (>1 = más lento) | `T.d(1.5)` → 1.5 s × tempo |
| `ease.in` | curva de lo que **llega** | entradas (`wipe`, `rise`, `grow`) |
| `ease.move` | curva de lo que **viaja** | desplazamientos largos, revelados de la capa base |
| `ease.settle` | curva del último tramo | asentamientos finales |
| `stagger` | retraso base entre hermanos | `T.gap(n)` → n pasos de stagger × tempo |
| `overshoot` | cuánto puede pasarse de su destino | 0 = nunca rebota; >0 solo con `back.out` |
| `hold` | silencio tras cada beat (s) | `T.hold` |
| `drift` | escala inicial de la cámara que se asienta hasta 1 | `kit.drift({from: T.drift})` |
| `cut` | si el corte seco es de la marca | forajido: sí |
| `rhythm`, `entrance` | etiqueta del carácter y del tipo de entrada | guía de diseño, no cambia el código |
| `avoid` | qué rompería la personalidad | revisar contra el storyboard |

## Elegir arquetipo

1. Si el caso de estudio del manual ya lo declara, **úsalo tal cual** (primario manda tempo y curvas; el secundario
   aporta *un* gesto: una entrada, un acento, un overshoot pequeño).
2. Si no, parte de la **motivación** y el **temor** del arquetipo (tabla del manual §2.2): el movimiento debe actuar
   la motivación y evitar el temor (un Inocente teme "hacer algo mal" → nada de glitches ni cortes bruscos).
3. Un solo primario. Mezclar más de dos produce un movimiento sin carácter.

## Sugerencias de partida para los casos del manual

Son puntos de partida derivados de los arquetipos que el propio manual les asigna, no decisiones del cliente:

| Marca | Arquetipos del manual | Tokens sugeridos | Idea de beat |
|---|---|---|---|
| AreMan (escudo) | Ancestro, Guardián, Buscador | `ancestro` (+ gesto simétrico `guardian`) | la montaña sostiene, el cóndor emerge, A+M se revelan |
| Albornoz Propiedades | Cuidador, Sabio local, Inocente | `cuidador` | los árboles "abrazan" la casa; la P aparece al asimetrizar el soporte |
| TommyBox | Sabio/Maestro, Mago, Explorador | `sabio` con acento de `mago` | círculo + T = persona; azul eléctrico como único color; degradado como transformación |
| SouthSoft | Sabio, Creador, Explorador | `sabio` | la S se corta y se vuelve ∞; "mejora continua" = loop con final definido (no repeat:-1) |
| BM3 Servicios | Sabio, Creador, Familia/Tribu | `cuidador` (tribu) con precisión de `creador` | tres cintas entran entrelazándose; el "3" se lee primero, B y M al final |
| OST Tech | Mago/Ingeniero, Guardián, Rebelde | `mago` o `guardian` | el engranaje gira; la S es el movimiento dentro de la máquina |

## Cuándo crear un arquetipo nuevo
Si la marca declara un arquetipo propio (ej. "Ancestro"), añade una entrada a `assets/motion-tokens.json` copiando la
más cercana y cambiando solo lo que de verdad difiere; escribe `avoid` con 2–3 cosas que romperían su carácter.
Ajustar `tempo` y `hold` suele cambiar más la percepción que cambiar las curvas.
