# Del análisis LogocodeX™ al storyboard de motion

El manual ya contiene el guion: cada logo tiene capas de lectura (Peirce), tres niveles de significado (Barthes)
y un mito. Un buen motion graphic no inventa una historia nueva; **hace visible, en el orden correcto, la que el
logo ya codifica**. Si el usuario no trae el análisis, haz primero los pasos 1–4 del método (identidad, arquetipo,
símbolos, traducción visual) de forma breve, o pídele el caso de estudio del manual.

## 1. Inventario de capas (qué se anima)

Lista cada capa del logo con tres datos, tomados del análisis semiótico:

| Capa | Tipo de signo (Peirce) | Qué significa / qué letra esconde |
|------|------------------------|-----------------------------------|
| ej. cóndor | ícono + índice + símbolo | apellido Manque; mensajero entre mundos; alas ≈ M |
| ej. montaña | ícono + símbolo | apellido Arellano; fundamento; ES la letra A |
| ej. árbol | ícono + índice | genealogía, "grabada en la piedra" |
| ej. nombre | símbolo (tipografía) | A y M en mayúscula = las dos iniciales |

Eso se traduce en cortes concretos de `split_logo_layers.py` (una capa = un significado). Si dos significados
comparten una forma (la montaña que es A), **no la partas**: esa doble lectura es el hallazgo del diseño.

## 2. Estructura de tres actos (Barthes)

| Acto | Pregunta que responde | Qué entra | Tipo de movimiento |
|------|----------------------|-----------|--------------------|
| **Denotación** | ¿Qué veo? | Lo literal: la forma base, lo icónico | Aparición directa, sin adornos, construcción de abajo hacia arriba o del centro hacia afuera |
| **Connotación** | ¿Qué significa para quien conoce el código? | Lo indicial y simbólico: el elemento "espíritu", el que añade la segunda lectura | Entrada con peso narrativo: emerge **de** algo anterior, no aparece de la nada |
| **Mito** | ¿Qué historia sostiene todo? | Nombre, tipomorfía revelada, remate | Pausa, revelación de la capa oculta, reposo en el logo exacto |

Regla de oro: **cada elemento nuevo debe nacer de uno ya presente** (el cóndor emerge de la montaña; el nombre cae
desde el símbolo). Es lo que el manual llama "cadena de asociaciones": nada flota solo.

## 3. Léxico de movimiento por tipo de signo (Peirce)

- **Ícono** (semeja): el movimiento imita la cosa real. Alas que se abren, árbol que crece desde la raíz, agua que sube.
- **Índice** (huella, causa): el movimiento deja rastro o consecuencia. Estela, trazo que se dibuja, sombra que llega después.
- **Símbolo** (convención): movimiento de **jerarquía**, no de imitación. Posición, escala, orden de lectura, color.

## 4. Tipomorfía: la escena firma

Cuando el logo esconde letras (A en la montaña, S = ∞, O = engranaje, B+M+3 en la triqueta), dedica un beat a
revelarlo. Patrón probado: **teñir la forma y su letra gemela en el nombre con el mismo acento, a la vez**, sostener,
volver al color canónico. Así se lee "esto es aquello" sin una línea de texto. Con éxito tipomórfico bajo (el manual
da 6/10 a la M de AreMan) hazlo igual, pero más corto: es una capa "para iniciados".

## 5. Simetría y ejes

Si el manual declara simetría bilateral (heráldica), las entradas **abren desde el eje central** (`wipe 'out-x'`) y
nunca desde un solo lado. Si el logo es asimétrico a propósito (asimetría intencional en Albornoz), conserva la
dirección de lectura del diseño: la animación sigue la asimetría, no la corrige.

## 6. Ritmo

- El tempo y los silencios vienen del arquetipo (`assets/motion-tokens.json`), no del gusto del día.
- Deja un silencio (`T.hold`) después de cada acto: es donde el espectador lee.
- Duración orientativa: 10–16 s para una pieza de identidad (reel / intro). Un logo-sting puro: 3–5 s con los mismos
  tres actos comprimidos (denotación 1 s, connotación 1.5 s, mito 1.5 s).
- Termina siempre en **reposo**: el último frame es el logo exacto, sin escala ni color alterados (regla de
  integridad del Manual de Aplicación Visual §5.1).

## 7. Paleta y color

Usa la paleta del manual de la marca (secc. 5.3). En marcas heráldicas monocromáticas (Sable y Argent) mantén
negro sobre papel y permite **un solo acento**, solo para revelar la capa oculta. Prohibido: cambiar colores
arbitrariamente, degradados que alteren el sentido, sombras que "ensucien" el símbolo.

## 8. Plantilla de brief (rellénala antes de tocar código)

```
MARCA / LOGO:        ____________   (archivo: ______ , capas: ______)
ARQUETIPO primario:  ____  secundario: ____   → tokens: tempo __, ease __, hold __
CAPAS Y SIGNIFICADO: (tabla del punto 1)
DENOTACIÓN (0–__ s): qué entra primero y cómo
CONNOTACIÓN (__–__ s): qué elemento nace de cuál
MITO (__–__ s):      nombre / tipomorfía / remate
BEAT TIPOMÓRFICO:    forma ↔ letra gemela, color de acento
FORMATO:             1080x1920 (reel) | 1080x1080 | 1920x1080   FPS 30   DURACIÓN ~__ s
REGLAS A VIGILAR:    (qué NO se puede hacer según el manual de la marca)
```
