# SPEC.md — convertir adjetivos en números antes de animar

Idea tomada de HyperFrames (HeyGen, Apache-2.0), reescrita. Un adjetivo ("premium", "moderno", "limpio") deja el hueco a los defaults del modelo, y los defaults se parecen entre sí: fondo oscuro, brillo, texto pequeño flotando al centro, todo en fade-in. Cada adjetivo convertido en número es una decisión recuperada.

Escribe `SPEC.md` en el proyecto (10–20 líneas) antes de tocar `timeline.js`, y revísalo con la hoja de contactos al final:

```
META:     qué siente o hace el espectador al final (1 frase)
SALIDA:   W x H, fps, duración = segundos x fps
LOOK:     fondo (hex, textura y %), tinta, UN acento y dónde puede aparecer;
          tipografía display + peso + tamaño px + tracking; cuerpo igual;
          medio (papel, producto, vidrio, arcilla, estudio 3D) con sus números;
          sombra (offset, blur, opacidad), grano %, viñeta %
OBJETOS:  cada cosa que el espectador debe reconocer, con material y detalles que la hagan legible sin etiqueta
MOVIMIENTO: curvas por rol (entrada, movimiento, salida, cámara), springs como amortiguación, duraciones y staggers
TOMAS:    una línea por toma: rango de segundos, el UN movimiento héroe, qué se lee, el sonido, cómo pasa a la siguiente
PROHIBIDO: los defaults de abajo + lo que esta pieza no debe parecer
QA:       fotogramas a revisar y qué debe mostrar cada uno
```

## Palabra → número
| Palabra | Se vuelve |
|---|---|
| premium | un material con cifras: papel satinado con 2 % de grano; producto sobre fondo continuo con sombra de contacto 0.55; cromo con rugosidad 0.05 |
| moderno | cámara y sistema tipográfico: empuje de 1 s con una sola curva; display al 9 % del alto del cuadro, tracking −2 % |
| limpio | una retícula y una ración: 12 columnas, márgenes 96 px, acento en una palabra por toma |
| dinámico | cortes al compás, cambio de layout cada 4 tiempos, un movimiento héroe por toma |
| juguetón | springs con amortiguación 0.45–0.6 sobre posición y escala (nunca sobre opacidad ni color), poses exageradas 10–30 % |
| cinematográfico | una lente y una luz: encuadre 35 mm, luz clave arriba-izquierda, contraluz, viñeta 6 % |

## Números de composición
- El héroe de una toma ocupa ≥ 40 % del alto o ancho. Un objeto pequeño en el centro de un cuadro vacío no es una toma: acércate, recorta o dale un mundo.
- Un movimiento héroe por toma; los secundarios recorren 50–70 % y empiezan 0.1–0.2 s después; el resto, quieto.
- Algo nuevo cada 2–4 s. Texto que se lee: ≥ 2.6 % del lado corto, visible 0.5 s + 0.3 s por palabra. Si hay demasiadas palabras, quita palabras; no encojas la letra.
- Tarjeta informativa: la información está en pantalla a ~2.5 s y se sostiene; cualquier fotograma pausado debe verse como un póster terminado.

## Defaults prohibidos (salvo que la marca o la referencia del usuario los use, y solo como los usa)
- fondo negro o azul marino con elementos pequeños flotando al centro;
- brillo, bloom, neón, destellos, orbes, partículas decorativas;
- degradados morado/azul, mesh gradients, tarjetas de vidrio;
- fondo crema + serif display + palabra en cursiva + etiquetas "01 / 02" + chips con forma de píldora;
- todo centrado; todo en fade-in a la vez; todo fade + slide-up;
- texto que se mueve mientras se lee; títulos que siguen a la deriva tras aterrizar;
- etiquetas de esquina, marcos, corchetes, lecturas tipo HUD como decoración.

> Las plantillas de este skill (kinetic, data, explainer, three) son **estructura**, no estilo: sus colores y su píldora CTA son marcadores. Si el SPEC no cambia el look, la pieza caerá en estos defaults.

## Pieza larga (> 15 s) que cuenta algo
Antes del SPEC, escribe tres argumentos distintos en palabras (tres películas diferentes, no tres versiones de la misma) y deja elegir al usuario, salvo que pida avanzar sin preguntas. Cada toma mueve la historia: lo que pasa causa la siguiente ("entonces…", "lo que significa…"), no eslóganes.
