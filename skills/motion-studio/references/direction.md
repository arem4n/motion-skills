# Dirección de movimiento

Marco adaptado (con palabras propias) de la capa de dirección del skill *motion-design* de LottieFiles (licencia MIT) y reescalado de milisegundos de UI a segundos de película. Léelo antes de escribir el timeline cuando la pieza no sea trivial.

## Tres pilares
1. **Jerarquía** — el orden del movimiento es el orden de lectura. Lo primero que se mueve es lo primero que debe verse.
2. **Causalidad** — nada aparece de la nada: tiene origen (de dónde viene), dirección (hacia dónde) y motivo (qué lo dispara). Un fade sin dirección es el recurso del que no decidió.
3. **Carácter** — la personalidad (tempo, curvas, rebote) es una decisión de marca, no un adorno.

## Tres capas de movimiento
- **Primaria**: lo que lleva el mensaje (titular, número, objeto héroe). Un héroe a la vez.
- **Secundaria**: lo que lo apoya (subtítulo, etiquetas, conectores). Entra *después* y más suave.
- **Ambiente**: cámara lenta, grano, deriva de fondo. Casi imperceptible; nunca compite.

## Reglas de un tercio
- Como máximo ~1/3 de los elementos se mueve a la vez.
- ~1/3 de la duración es quietud con significado (el ojo lee).
- Las capas secundarias usan ~1/3 de la amplitud de la primaria.

## Cuatro actos
1. **Gancho** (0–0.6 s hasta el primer cambio visible): algo se mueve o aparece ya.
2. **Desarrollo**: construye la idea, un elemento por vez.
3. **Golpe**: el momento de mayor energía; coincide con un cue de sonido y, si hay cámara, con su pico.
4. **Resolución**: todo quieto ≥ 0.5 s; el mensaje final se lee sin competencia.

## Tiempos (en segundos de película, ×tempo de la personalidad)
| Cosa | Duración base |
|---|---|
| Entrada de elemento | 0.45–0.7 |
| Salida | 60–70 % de la entrada |
| Stagger entre elementos | 0.07–0.14 (presupuesto: la cascada completa ≤ 0.9 s) |
| Transición de escena | 0.45–0.6 |
| Pausa de lectura | ≈ 0.25 s por palabra de apoyo, mínimo 0.8 s |
| Hold final | `T.hold` (0.25 impact … 1.1 calm) + margen |

## Personalidades
`playful` rebota y es rápido · `premium` lento, expo.out, sin rebote · `corporate` claro, parejo · `energetic` corto y cortante · `calm` largo y legato · `impact` golpes secos, pausas duras. Cada una declara qué evitar (`avoid`) — respétalo.

## Anticipación y arrastre (lo que separa "se mueve" de "está vivo")
Dos principios clásicos de animación que las plantillas no traen puestos; úsalos en el héroe, no en todo.
- **Anticipación**: antes de un movimiento grande, un gesto corto en sentido contrario (5–10 % del recorrido, 0.08–0.15 s). En una salida ya viene
  hecha con `ease: 'back.in(1.4)'`; en un lanzamiento, un tween previo: `tl.to(el, { y: '+=14', duration: T.d(0.12), ease: 'power1.out' }, at - T.d(0.12))`.
  Sirve para golpes, lanzamientos y salidas del héroe. No en `premium` ni `calm` (su tabla de personalidad evita rebotes).
- **Arrastre y solapamiento**: lo que cuelga del héroe llega después y se pasa un poco. El subtítulo, la sombra o la etiqueta arrancan 0.1–0.2 s
  más tarde que su titular y con ~1/3 de su amplitud; nunca todo aterriza en el mismo fotograma. Con `stagger` ya ocurre entre palabras;
  hazlo también **entre capas** (primaria → secundaria).
- Presupuesto: una anticipación por toma. Si todo anticipa, nada pesa.

## Curvas
- Entradas: desaceleran (`ease.in`, p. ej. power3.out). Salidas: aceleran (`ease.out`). En pantalla: inout (`ease.move`). Énfasis elástico: `ease.pop` solo en personalidades que lo admiten.
- Nunca `linear` para movimiento visible (sí para grano o deriva).

## Lista de calidad (pásala antes de renderizar)
- [ ] ¿Se entiende el mensaje con el sonido apagado?
- [ ] ¿Hay un solo héroe en cada momento?
- [ ] ¿Cada movimiento tiene origen y dirección?
- [ ] ¿Cada golpe visual tiene cue de sonido en su fotograma?
- [ ] ¿Hay gancho ≤ 0.6 s y final quieto?
- [ ] ¿Todo dato viene del encargo?
- [ ] ¿La personalidad se nota (tempo/curvas) y respeta su `avoid`?

## Diagnóstico rápido
| Síntoma | Causa probable | Arreglo |
|---|---|---|
| Se siente "de PowerPoint" | todo fade/slide igual, sin héroe | un golpe de mayor amplitud + cámara + sonido |
| Caótico | >1/3 en movimiento, staggers largos | recortar simultaneidad, presupuesto de stagger |
| Lento/aburrido | tempo alto o pausas > 1 s sin razón | bajar `tempo`, acortar holds |
| Texto ilegible | tamaño < 2.8 %, contraste, zona insegura | el validador lo marca |
| Se acaba de golpe | sin hold | `T.hold` + 0.5 s |

## Ley de vectores entre escenas (de la "motion doctrine" de HyperFrames, adaptada)
Una pieza de varias escenas debe sentirse como UN movimiento de cámara continuo, no como diapositivas animadas por separado.
1. **Eje**: x sigue siendo x, y sigue siendo y, Z sigue siendo Z. Nunca cambies de eje en un corte.
2. **Dirección**: no la espejes. En Z la dirección es el signo del cambio de escala: crecer = avanzar, encogerse = retroceder. Una salida que se aleja respondida por una entrada que crece desde pequeño es un vector espejado (el error más común, porque "crecer desde pequeño" es la entrada por defecto).
3. **Velocidad**: la entrada arranca con la velocidad con que terminó la salida (curvas espejadas: salida `power4.in` + entrada `power4.out`, misma distancia y duración).
4. **Fase**: el corte cae a mitad de movimiento en ambos lados; frenar antes del corte o arrancar desde reposo después es un tiempo muerto.
- **La corriente**: elige UNA dirección dominante para toda la pieza (por defecto, izquierda) para los cortes normales; las demás son "reservadas" y significan algo (arriba = revelación/conclusión; zoom hacia dentro = profundizar; zoom hacia fuera = llegada de algo grande).
- Nunca encadenes cortes en direcciones opuestas (ping-pong se lee como error), salvo con una causa visible o cambio de capítulo.
- **Portadores**: el ojo sigue objetos, no abstracciones. Pasa un objeto concreto a través del corte (un contenedor que se encoge hacia el siguiente layout, una marca que vuela a su sitio). Nunca un crossfade: no tiene portador.
- **Movimiento causal**: cada movimiento lo dispara el anterior (golpe → squash → liberación → vuelo → impacto → rebote → revelación); el efecto empieza en el mismo fotograma de su causa; las reacciones escalan con la masa (lo grande rebota lento, lo pequeño seca).
- **Sin vaivén ocioso**: el movimiento debe *actuar*, no respirar. Tras aterrizar, un elemento no deriva ni "flota" mientras se lee. Quietud antes del clímax.
Esto no se verifica automáticamente en este skill (HyperFrames sí tiene un "seam gate"); anótalo en el SPEC como tabla de cortes (salida, entrada, dirección) y revísalo en la hoja de contactos.
