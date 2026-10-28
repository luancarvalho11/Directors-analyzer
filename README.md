[README.md](https://github.com/user-attachments/files/34053489/README.md)
# 🎬 Letterboxd - Analisador de Diretores Mais Assistidos

[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://directors-analyzer-lgvnbpdxl7mvw4yyackles.streamlit.app/)

Uma aplicação web desenvolvida em Python e Streamlit que analisa o arquivo `.zip` exportado da sua conta no **Letterboxd**, cruza os dados com a API do **TMDb (The Movie Database)** e revela quem são os **diretores que você mais assistiu**, apresentando gráficos interativos e um relatório em PDF pronto para download!

👉 **Acesse a aplicação no ar:** [directors-analyzer.streamlit.app](https://directors-analyzer-lgvnbpdxl7mvw4yyackles.streamlit.app/)

---

## ✨ Funcionalidades

- 📂 **Upload Simples:** Aceita diretamente o arquivo `.zip` exportado do Letterboxd (sem precisar descompactar).
- ⚡ **Busca Paralela & Otimizada:** Consultas assíncronas/multi-thread à API do TMDb com cache local de títulos.
- 📊 **Gráficos & Métricas:**
  - Total de diretores distintos e diretor favorito.
  - Gráfico horizontal do **Top 15** diretores.
  - Relação detalhada de filmes assistidos por diretor e suas respectivas notas.
- 📄 **Exportação em PDF:** Geração de um relatório visual e formatado com a lista dos diretores e filmes avaliados.

---

## 🚀 Como Usar e Testar

### 1. Obtenha seus dados do Letterboxd
1. Entre na sua conta em [letterboxd.com](https://letterboxd.com).
2. Vá em **Settings** > aba **Data**.
3. Clique em **"Export Your Data"** e baixe o arquivo `.zip`.
   > 💡 *Dica:* Para ter resultados interessantes nos gráficos, certifique-se de ter pelo menos 15 a 20 filmes registrados, com mais de um filme dos mesmos diretores (ex: Nolan, Tarantino, Spielberg, etc.).

### 2. Analisar no App
1. Acesse o app: [directors-analyzer.streamlit.app](https://directors-analyzer-lgvnbpdxl7mvw4yyackles.streamlit.app/).
2. Faça o upload do seu arquivo `.zip`.
3. Clique em **"🚀 Analisar Meus Diretores"**.
4. Veja o ranking, explore os gráficos e baixe o seu **Relatório em PDF**!

---

## 🛠️ Tecnologias Utilizadas

- **[Python](https://www.python.org/)**
- **[Streamlit](https://streamlit.io/)** — Interface web interativa
- **[ReportLab](https://www.reportlab.com/)** — Geração de relatórios PDF
- **[TMDb API](https://www.themoviedb.org/)** — Consulta de ficha técnica e diretores
