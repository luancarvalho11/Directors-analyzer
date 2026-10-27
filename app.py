import os
import io
import json
import zipfile
import csv
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests
import streamlit as st
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfgen import canvas

# Page config
st.set_page_config(
    page_title="Letterboxd - Diretores Mais Assistidos",
    page_icon="🎬",
    layout="wide"
)

# Obter chave das Secrets do Streamlit se configurada, ou fallback para entrada manual
DEFAULT_API_KEY = st.secrets.get("TMDB_API_KEY", "")

CACHE_FILE = "tmdb_directors_cache.json"

def load_cache():
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_cache(cache):
    try:
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(cache, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

def fetch_director(title, year, api_key, cache):
    key = f"{title.strip().lower()}_{str(year).strip()}"
    if key in cache:
        return title, year, cache[key]

    headers = {"accept": "application/json"}
    search_url = "https://api.themoviedb.org/3/search/movie"
    params = {
        "api_key": api_key,
        "query": title,
        "language": "pt-BR"
    }
    if year:
        params["year"] = str(year)

    try:
        resp = requests.get(search_url, params=params, headers=headers, timeout=5)
        if resp.status_code == 200:
            results = resp.json().get("results", [])
            # Fallback if with year returned nothing
            if not results and year:
                params.pop("year", None)
                resp = requests.get(search_url, params=params, headers=headers, timeout=5)
                if resp.status_code == 200:
                    results = resp.json().get("results", [])

            if results:
                movie_id = results[0]["id"]
                cred_url = f"https://api.themoviedb.org/3/movie/{movie_id}/credits"
                c_resp = requests.get(cred_url, params={"api_key": api_key}, headers=headers, timeout=5)
                if c_resp.status_code == 200:
                    crew = c_resp.json().get("crew", [])
                    directors = [c["name"] for c in crew if c.get("job") == "Director"]
                    if not directors:
                        directors = ["Diretor Desconhecido"]
                    cache[key] = directors
                    return title, year, directors
    except Exception:
        pass

    directors = ["Não Encontrado"]
    cache[key] = directors
    return title, year, directors

def parse_letterboxd_zip(uploaded_file):
    with zipfile.ZipFile(uploaded_file) as z:
        def read_csv(name):
            if name not in z.namelist():
                return []
            raw = z.read(name)
            try:
                text = raw.decode("utf-8")
            except UnicodeDecodeError:
                text = raw.decode("latin-1", errors="ignore")
            return list(csv.DictReader(io.StringIO(text)))

        watched = read_csv("watched.csv")
        ratings = read_csv("ratings.csv")
        profile = read_csv("profile.csv")

    rating_map = {}
    for r in ratings:
        uri = r.get("Letterboxd URI", "")
        if uri:
            rating_map[uri] = r.get("Rating", "")
        # fallback by (Name, Year)
        rating_map[(r.get("Name", "").strip().lower(), str(r.get("Year", "")).strip())] = r.get("Rating", "")

    for w in watched:
        uri = w.get("Letterboxd URI", "")
        k = (w.get("Name", "").strip().lower(), str(w.get("Year", "")).strip())
        w["Rating"] = rating_map.get(uri) or rating_map.get(k, "")

    username = profile[0].get("Username", "Usuário") if profile else "Usuário"
    return username, watched

class NumberedCanvas(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, page_count):
        self.saveState()
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#718096"))
        if self._pageNumber > 1:
            self.drawString(54, 755, "Ranking de Diretores Mais Assistidos - Letterboxd")
            self.setStrokeColor(colors.HexColor("#E2E8F0"))
            self.setLineWidth(0.5)
            self.line(54, 747, 558, 747)

        footer_text = f"Página {self._pageNumber} de {page_count}"
        self.drawRightString(558, 35, footer_text)
        self.drawString(54, 35, "Gerado via TMDb & Letterboxd")
        self.setStrokeColor(colors.HexColor("#E2E8F0"))
        self.setLineWidth(0.5)
        self.line(54, 45, 558, 45)
        self.restoreState()

def generate_pdf(username, sorted_directors, director_movies):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        leftMargin=54,
        rightMargin=54,
        topMargin=54,
        bottomMargin=54
    )
    styles = getSampleStyleSheet()
    
    PRIMARY = colors.HexColor("#1A202C")
    ACCENT = colors.HexColor("#2B6CB0")
    BORDER_COLOR = colors.HexColor("#CBD5E0")
    BG_LIGHT = colors.HexColor("#F7FAFC")

    title_s = ParagraphStyle('Title', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=20, leading=24, textColor=PRIMARY)
    sub_s = ParagraphStyle('Sub', parent=styles['Normal'], fontName='Helvetica', fontSize=10, leading=14, textColor=colors.HexColor("#4A5568"))
    cell_h = ParagraphStyle('CH', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=9, leading=12, textColor=colors.white)
    cell_s = ParagraphStyle('CS', parent=styles['Normal'], fontName='Helvetica', fontSize=8.5, leading=11, textColor=PRIMARY)
    cell_b = ParagraphStyle('CB', parent=cell_s, fontName='Helvetica-Bold')
    cell_m = ParagraphStyle('CM', parent=cell_s, textColor=colors.HexColor("#718096"))

    story = [
        Paragraph(f"Diretores Mais Assistidos", title_s),
        Spacer(1, 4),
        Paragraph(f"Relatório de perfil: <b>@{username}</b> | Dados obtidos via Letterboxd + TMDb API", sub_s),
        Spacer(1, 10),
        HRFlowable(width="100%", thickness=1.5, color=ACCENT, spaceBefore=0, spaceAfter=14)
    ]

    table_data = [[
        Paragraph("<b>#</b>", cell_h),
        Paragraph("<b>Diretor(a)</b>", cell_h),
        Paragraph("<b>Filmes Vistos</b>", cell_h),
        Paragraph("<b>Filmes Registrados (Amostra / Notas)</b>", cell_h)
    ]]

    for rank, (director, count) in enumerate(sorted_directors[:40], start=1):
        movies = director_movies[director]
        sample_list = []
        for m in movies[:4]:
            t = m['name']
            y = f" ({m['year']})" if m['year'] else ""
            r = f" [{m['rating']}★]" if m['rating'] else ""
            sample_list.append(f"{t}{y}{r}")
        sample_str = "; ".join(sample_list)
        if len(movies) > 4:
            sample_str += f" e mais {len(movies)-4}..."

        table_data.append([
            Paragraph(str(rank), cell_m),
            Paragraph(f"<b>{director}</b>", cell_b),
            Paragraph(str(count), cell_b),
            Paragraph(sample_str, cell_s)
        ])

    table = Table(table_data, colWidths=[26, 130, 68, 280], repeatRows=1)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), ACCENT),
        ('ALIGN', (0,0), (0,-1), 'CENTER'),
        ('ALIGN', (2,0), (2,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('GRID', (0,0), (-1,-1), 0.5, BORDER_COLOR),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, BG_LIGHT]),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
    ]))
    story.append(table)

    doc.build(story, canvasmaker=NumberedCanvas)
    buffer.seek(0)
    return buffer.getvalue()


# Interface
st.title("🎬 Diretores Mais Assistidos do Letterboxd")
st.markdown("Faça o upload do arquivo `.zip` exportado da sua conta no Letterboxd para descobrir os diretores que você mais assistiu.")

with st.sidebar:
    st.header("⚙️ Configuração")
    if DEFAULT_API_KEY:
        st.success("🔑 Chave TMDb configurada no servidor!")
        api_key_input = DEFAULT_API_KEY
    else:
        api_key_input = st.text_input("Chave da API do TMDb:", type="password", help="Insira a sua API Key (v3 auth) gerada no themoviedb.org")
        st.caption("A chave é usada para consultar os diretores de cada filme.")
    st.markdown("---")
    st.caption("O sistema faz cache automático para agilizar buscas futuras.")

uploaded_file = st.file_uploader("Selecione o arquivo .zip do Letterboxd:", type=["zip"])

if uploaded_file and api_key_input:
    username, watched = parse_letterboxd_zip(uploaded_file)
    st.success(f"Arquivo carregado com sucesso! Usuário: **@{username}** | Total de filmes assistidos: **{len(watched)}**")

    if st.button("🚀 Analisar Meus Diretores", type="primary"):
        cache = load_cache()
        progress_bar = st.progress(0)
        status_text = st.empty()

        director_counts = Counter()
        director_movies = defaultdict(list)

        total_movies = len(watched)
        completed = 0

        status_text.text("Consultando diretores na base do TMDb...")

        with ThreadPoolExecutor(max_workers=8) as executor:
            futures = [
                executor.submit(fetch_director, w.get("Name", ""), w.get("Year", ""), api_key_input.strip(), cache)
                for w in watched
            ]
            for f in as_completed(futures):
                title, year, directors = f.result()
                rating = ""
                # Find rating from watched
                for w in watched:
                    if w.get("Name") == title and w.get("Year") == year:
                        rating = w.get("Rating", "")
                        break

                for d in directors:
                    if d not in ("Não Encontrado", "Diretor Desconhecido"):
                        director_counts[d] += 1
                        director_movies[d].append({"name": title, "year": year, "rating": rating})

                completed += 1
                progress_bar.progress(completed / total_movies)
                if completed % 15 == 0 or completed == total_movies:
                    status_text.text(f"Processando: {completed} de {total_movies} filmes verificados...")

        save_cache(cache)
        status_text.success("Análise concluída com sucesso!")

        sorted_directors = director_counts.most_common()

        # Display Metrics
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total de Diretores Distintos", len(sorted_directors))
        with col2:
            top_dir = sorted_directors[0][0] if sorted_directors else "-"
            top_count = sorted_directors[0][1] if sorted_directors else 0
            st.metric("Diretor Mais Assistido", f"{top_dir} ({top_count} filmes)")
        with col3:
            pdf_bytes = generate_pdf(username, sorted_directors, director_movies)
            st.download_button(
                label="📥 Baixar Relatório em PDF",
                data=pdf_bytes,
                file_name=f"Diretores_Mais_Assistidos_{username}.pdf",
                mime="application/pdf"
            )

        # Tabs for visualization
        tab_top, tab_table = st.tabs(["🏆 Top 15 Gráfico", "📋 Tabela Completa"])

        with tab_top:
            top15 = sorted_directors[:15]
            if top15:
                chart_data = {d[0]: d[1] for d in reversed(top15)}
                st.bar_chart(chart_data, horizontal=True)

        with tab_table:
            st.subheader("Ranking Geral")
            for rank, (director, count) in enumerate(sorted_directors[:50], start=1):
                with st.expander(f"#{rank} - **{director}** — {count} filme(s) assistido(s)"):
                    movies = director_movies[director]
                    for m in movies:
                        r_str = f" • Avaliação: {m['rating']}★" if m['rating'] else ""
                        st.markdown(f"- **{m['name']}** ({m['year']}){r_str}")

elif uploaded_file and not api_key_input:
    st.info("👆 Por favor, informe sua Chave de API do TMDb na barra lateral à esquerda para iniciar.")
