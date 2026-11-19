# QA por entidad (`scripts/entity_qa.py`)

Idea de Diorama (sloemo01, MIT): una pieza puede parecer viva porque algo se mueve, mientras un actor que importa está muerto,
fuera de cuadro o quieto. `validate.py` mira la escena entera (¿hay movimiento? ¿se lee?); `entity_qa.py` mira **cada elemento**.

```bash
$PY -I scripts/entity_qa.py --scene proy/scene.html --size 1080x1920 [--fps 30] [--report ent.json]
```

No hace capturas: mide la caja y la opacidad de cada elemento en **cada fotograma** con el DOM (≈1,5 s para 4,6 s de escena).

| Veredicto | Significa | Nivel |
|---|---|---|
| `EMPTY` | nunca visible en toda la línea de tiempo (opacidad, `visibility` o caja < 2 px) | FAIL si declarado, WARN si no |
| `OFFSCREEN` | visible, pero su caja nunca toca el cuadro | idem |
| `FROZEN` | `data-expect="moves"` y estuvo > 1 s visible sin cambiar de caja ni opacidad | FAIL (solo declarados) |
| `TELEPORT` | su centro salta > 25 % del lado corto en UN fotograma mientras es visible en ambos | WARN |

**Declarar una entidad** (lo que "debe cumplir"): `el.dataset.entity = 'logo'; el.dataset.expect = 'moves';` sobre el elemento que devuelven
`MG.text/box/shape/img`. Sin `data-entity` solo hay avisos.

Detalles que importan:
- La caja de `FROZEN` se mide **relativa a `.mg-world`**: un empuje de cámara no cuenta como movimiento del elemento.
- `TELEPORT` es solo aviso: puede dar falso positivo en texto con máscara (`how:'mask'`), cuya caja cambia al revelarse. Comprueba con la hoja de contactos.
- Un texto creado **a propósito sin contenido** (p. ej. `head(titulo, '')`, un titular sin subtítulo) sale `EMPTY` como WARN: es correcto y inofensivo.
- Los fondos a cuadro completo no cuentan como actores.
- No ve texto del DOM tapado por geometría 3D ni etiquetas sobre un objeto del canvas: eso sigue siendo cosa de la hoja de contactos.
- Verificado con una escena con tres casos plantados (uno muerto, uno quieto que debía moverse, uno que salta): detecta los tres.
