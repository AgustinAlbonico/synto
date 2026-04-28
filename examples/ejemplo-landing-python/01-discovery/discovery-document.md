# Discovery Document

## Información general

- **Proyecto**: ejemplo-landing-python
- **Fecha**: 2026-04-27
- **Facilitador**: Agustín Albonico

---

## 1. ¿Qué problema resolvemos?

Necesitamos una landing page simple pero profesional para presentar un servicio de consultoría tecnológica. El objetivo es captar leads mediante un formulario de contacto.

- Problema principal: No tenemos presencia web profesional
- ¿Por qué es importante? Los clientes potenciales buscan credibilidad online
- ¿Quién lo sufre? El consultor que no tiene forma de captar leads digitales

---

## 2. ¿Para quién lo resolvemos?

### Persona 1: Decision-maker Tech
- **Rol**: CTO o Tech Lead de startup
- **Edad / Background**: 30-45 años, busca consultoría para acelerar desarrollo
- **Goals**: Encontrar un consultor confiable rápidamente
- **Frustraciones**: Páginas confusas, formularios largos, no saber qué servicios ofrecen
- **Tecnología que usa**: Laptop, Chrome, email

### Persona 2: Emprendedor no-técnico
- **Rol**: Founder de startup early-stage
- **Edad / Background**: 25-40 años, necesita validar idea técnica
- **Goals**: Entender si el consultor puede ayudar en su stack
- **Frustraciones**: Jerga técnica excesiva, falta de claridad en pricing
- **Tecnología que usa**: Mobile principalmente

---

## 3. ¿Qué sabemos hoy?

- Datos que ya tenemos: El consultor trabaja con Python, React, y cloud
- Supuestos que estamos haciendo: Los clientes prefieren formulario simple a chatbot
- Lo que no sabemos: Tasa de conversión esperada

---

## 4. ¿Qué necesitamos aprender?

- ¿Qué campos del formulario maximizan conversiones?
- ¿Qué tono de comunicación resuena mejor?

---

## 5. Alternativas existentes

- **Carrd.co**: Muy simple, poco customizable
- **Webflow**: Poderoso pero overkill para una landing simple
- **WordPress + Elementor**: Flexible pero requiere mantenimiento

---

## 6. Restricciones técnicas

- Stack: Python (Flask) + HTML/CSS + SQLite
- Hosting: VPS propio o Railway/Render
- No se necesita CMS, contenido estático
- Debe cargar en < 2s

---

## 7. Alcance tentativo

### In-scope (MVP)
- [ ] Hero section con value proposition
- [ ] Sección de servicios
- [ ] Formulario de contacto
- [ ] Footer con links sociales
- [ ] Responsive design

### Out-of-scope
- [ ] Blog
- [ ] Multi-idioma
- [ ] Dashboard admin

---

## 8. Preguntas para el usuario

- ¿Tenés dominio propio?
- ¿Preferís deploy en Render, Railway o VPS?
- ¿Necesitás analytics (Google Analytics, Plausible)?

---

## 9. Decisiones preliminares

- Stack sugerido: Flask + Jinja2 + Tailwind CSS (via CDN)
- Base de datos: SQLite para guardar leads
- Hosting: Render (free tier)
- Riesgos: Tailwind CDN puede ser lento, considerar build step si escala

---

## 10. Próximos pasos

- [ ] Validar stack con usuario
- [ ] Definir PRD
- [ ] Definir spec técnico
