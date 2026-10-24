# 🏀 Cadet Interterritorial · Catalunya

Aplicación web para seguir la **Cadet Interterritorial** masculina y femenina de la [Federació Catalana de Basquetbol](https://www.basquetcatala.cat/): mapa de Catalunya por municipios, clasificaciones por grupo y ficha de cada equipo.

Una sola página HTML, sin frameworks ni build steps.

---

## ✨ Características

### Mapa de Catalunya
- Los 947 municipios de Catalunya, con zoom y arrastre (rueda / pellizco)
- Un punto por municipio con equipo, coloreado por grupo y con el número de equipos si hay varios
- Los equipos del grupo seleccionado se resaltan
- Botón **Àrea de Barcelona** para acercar la zona metropolitana, donde se concentran la mayoría de equipos
- Tooltip con los equipos de cada municipio (grupo y posición)

### Clasificación
- Interruptor **MASC / FEM**
- Pestañas por grupo (8 masculinos, 6 femeninos en 2026-27)
- J, G, P, PF, PC y puntos; al hacer clic en un equipo se selecciona en el mapa

### Ficha de equipo
Al pinchar un equipo (en la clasificación, el mapa, el buscador o un partido) la zona principal muestra **solo ese equipo**:
- Escudo del club, también en la clasificación, los resultados y el buscador (si no carga, se ven sus iniciales)
- Posición, balance, puntos, puntos a favor / en contra por partido y diferencia
- **Próximo partido** destacado: rival, cuenta atrás ("En 6 días"), pabellón y cómo llegar
- **Forma**: gráfico con la diferencia de puntos de los últimos partidos, racha, balance en casa y fuera, distancia al líder y ranking de ataque y defensa dentro del grupo
- Últimos resultados y siguientes partidos; al pinchar en un rival se abre su ficha
- Pabellón con dirección y día y hora habitual de juego en casa
- **Último partido · por jugador**: box score del último partido jugado (rival, marcador y fecha), del equipo y del rival (lado a lado en escritorio, uno debajo del otro en móvil), con minutos, puntos, tiros de 2 y triples anotados, tiros libres (anotados/intentados y %), faltas y +/−; quien no jugó aparece como «No jugó»
- **Jugadores**, a todo el ancho: nombre abreviado ("Pol H.") con partidos, minutos (totales y por partido), puntos (totales y por partido), tiros de 2 y triples anotados, tiros libres (anotados/intentados y %), faltas por partido y % de los puntos del equipo, más una fila con el total del equipo
  - Se ordena pulsando cualquier columna (otra vez para invertir); por defecto, por anotación
  - Líderes del equipo: máximo anotador, más triples, mejor en tiros libres (mín. 10 intentos) y más minutos
  - La Federació solo publica los tiros de 2 y triples anotados (no los intentos) y las faltas por partido redondeadas
- Otros equipos del mismo municipio, con un botón para verlos todos

Al pinchar un municipio con varios equipos se muestra la lista para elegir uno; si solo tiene uno, se abre directamente su ficha.

- **⭐ Mi equipo**: marca equipos como favoritos (se guardan en el navegador); aparecen arriba del resumen con su posición y próximo partido, y con ★ en la clasificación
- **🧭 Cómo llegar**: abre el pabellón en Google Maps
- **📅 Añadir al calendario**: descarga un `.ics` con todos los partidos pendientes del equipo (Google Calendar, Apple, Outlook…)
- **🔗 Compartir**: copia el enlace directo al equipo
- **Calendario completo** desplegable con todos los partidos de la fase

### Buscador
- Busca equipos (masculinos y femeninos), clubs, municipios y pabellones, sin importar tildes ni mayúsculas
- Navegable con teclado (↑ ↓ Enter Esc); la tecla `/` lo enfoca desde cualquier sitio
- Al elegir un resultado cambia de categoría si hace falta y centra el mapa en el municipio

### Enlaces compartibles
- La URL refleja la categoría, el grupo y el equipo o municipio seleccionado (`#sexo=F&grupo=23373&equipo=89331`), así que se puede guardar o enviar, y el botón Atrás del navegador deshace la última selección

### Resumen (sin selección)
- Mis equipos, líderes de cada grupo, máximos anotadores, partidos de los próximos 7 días, mejores ataques y defensas

### ♿ Accesibilidad (baja visión)
- Menú **Aa · Accesibilidad** en la cabecera, con preferencias que se recuerdan:
  - **Tamaño de letra** 100 % · 115 % · 130 % · 150 %: escala textos, columnas, insignias y puntos del mapa. Si la clasificación se queda estrecha, oculta PF y PC para que se lean los nombres
  - **Alto contraste**: fondo negro, texto blanco y acento amarillo, con bordes visibles
  - **Reducir animaciones**: sin transiciones ni zoom animado
- La primera vez se respetan las preferencias del sistema (modo oscuro, más contraste, menos movimiento)
- Contraste **WCAG AA (≥ 4,5:1)** en todos los textos en modo claro, oscuro y alto contraste; letra mínima de 11 px
- Todo se puede usar con **teclado**: grupos, filas de la clasificación, tarjetas, leyenda y los puntos del mapa (Tab + Enter), con foco siempre visible; enlace "Saltar a la clasificación"
- **Lectores de pantalla**: encabezados, etiquetas descriptivas ("2º CB Banyoles, Banyoles: 3 ganados, 3 perdidos, 9 puntos") y avisos de la selección actual

### Otros
- **Idioma**: catalán (por defecto) o castellano, con el botón **CA · ES** de la cabecera; se recuerda en el navegador. Los textos se escriben en castellano en el código y pasan por `tr()`, que busca su versión catalana en la tabla `CA` de `index.html`
- Diseño de escritorio en dos columnas: a la izquierda la clasificación con el mapa debajo, y la ficha de equipo como zona principal
- La columna izquierda se puede ensanchar arrastrando el separador (doble clic restablece el ancho; también con las flechas del teclado); el mapa crece con ella. El ancho se recuerda, y cuando hay varios equipos se muestran en dos columnas
- Tema claro / oscuro
- Versión móvil con navegación inferior (Clasificación · Mapa · Equipo)

---

## 🚀 Cómo usar

Abre `index.html` en el navegador. No requiere servidor.

```bash
xdg-open index.html
```

---

## 🔄 Actualizar los datos

Los datos son una **copia estática** (`data/cadet-data.js`). basquetcatala.cat está protegida con una verificación reCAPTCHA y no permite peticiones desde otras webs, así que no se puede consultar en vivo: hay que extraer los datos desde un navegador.

1. Abre <https://www.basquetcatala.cat/> y espera a que pase la verificación de seguridad.
2. Abre la consola (F12 → **Console**), pega el contenido de [`scripts/extract.js`](scripts/extract.js) y pulsa Enter.
   Recorre todos los grupos y equipos y el último partido de cada equipo (~4-5 minutos, con pausas para no cargar el servidor) y descarga `fcbq_raw.json`.
3. Genera los datos de la página (y, con `--push`, haz commit y push):

   ```bash
   python3 scripts/update.py --push
   ```

   Coge el `fcbq_raw*.json` más reciente de la carpeta de descargas (o el que se le pase como argumento), lo copia a `data/fcbq_raw.json`, ejecuta `build_data.py` y muestra cuántos partidos nuevos hay. Sin `--push` solo actualiza los archivos.

El extractor localiza la categoría por su nombre ("Cadet … Interterritorial") en la temporada actual, así que sirve también para temporadas futuras mientras la web mantenga su estructura.

---

## 📁 Estructura

```
index.html              Página (HTML + CSS + JS)
data/
  cadet-data.js         Datos que usa la página (generado)
  fcbq_raw.json         Datos extraídos de basquetcatala.cat
scripts/
  extract.js            Extractor para la consola del navegador
  build_data.py         fcbq_raw.json → cadet-data.js (asigna municipio a cada equipo)
  update.py             Descargas → data/, regenera los datos y opcionalmente commit + push
```

## 🛠️ Tecnologías

| Tecnología | Uso |
|---|---|
| **HTML / CSS / JavaScript** | Página única, sin build |
| **D3.js v7** | Mapa SVG, proyección Mercator y zoom |
| **TopoJSON** + [`es-atlas`](https://www.npmjs.com/package/es-atlas) | Municipios y provincias de Catalunya |
| **Python 3** | Script de generación de datos (solo biblioteca estándar) |

---

## 🔒 Privacidad

- No se guardan los datos de contacto de los responsables de club (nombre, teléfono, email) que muestran las fichas de equipo de la web.
- Los jugadores son menores de edad: solo se guarda el **nombre abreviado** (nombre + inicial del primer apellido, o las iniciales cuando la Federació ya las publica así) y sus estadísticas. La abreviatura se hace en el navegador durante la extracción, así que el nombre completo no llega a ningún archivo del proyecto. No se guardan fotos ni otros datos, y los nombres de jugadores no son buscables.
- Los escudos se cargan desde el servidor de imágenes de la Federació (no se guardan en el proyecto), así que necesitan conexión; sin ella se ven las iniciales del club.
- Las estadísticas de jugadores salen de las actas digitales de la Federació; algunos partidos no las tienen, así que pueden no sumar todos los puntos del equipo.

## 📝 Licencia

Proyecto de uso personal / educativo. Los datos de competición proceden de la Federació Catalana de Basquetbol (basquetcatala.cat).
