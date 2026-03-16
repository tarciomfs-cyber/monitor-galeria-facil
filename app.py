import streamlit as st
from pytrends.request import TrendReq
import pandas as pd
import plotly.express as px
import urllib.parse
import numpy as np

# Configuração da Página
st.set_page_config(page_title="Galeria Fácil - Inteligência 360", layout="wide")

# Inicializar Pytrends
try:
    pytrends = TrendReq(hl='pt-BR', tz=360)
except:
    st.error("Erro de conexão. Tente novamente.")

# --- BARRA LATERAL: CALCULADORA ---
with st.sidebar:
    st.header("🧮 Calculadora de Lucro")
    custo = st.number_input("Custo (R$)", value=50.0)
    venda = st.number_input("Venda (R$)", value=120.0)
    comissao = st.slider("Comissão (%)", 0, 30, 11)
    frete = st.number_input("Frete (R$)", value=6.0)
    lucro = venda - custo - (venda * (comissao/100)) - (venda * 0.06) - frete
    st.metric("Lucro Líquido", f"R$ {lucro:.2f}", delta=f"{(lucro/venda)*100:.1f}% Margem" if venda > 0 else "0%")

# --- NAVEGAÇÃO POR ABAS ---
tab1, tab2 = st.tabs(["🏆 Top 15 Oportunidades", "⚖️ Comparador & Projeção"])

# --- ABA 1: TOP 15 PRODUTOS ---
with tab1:
    st.header("🔥 Melhores Produtos para Avaliar (Brasil)")
    st.info("Estes são os termos com maior crescimento de busca nas últimas 24h.")
    
    if st.button("🔄 Atualizar Lista de Oportunidades"):
        try:
            # Busca tendências diárias
            df_trending = pytrends.trending_searches(pn='brazil')
            top_15 = df_trending.head(15)
            top_15.columns = ['Termo em Ascensão']
            
            # Criar colunas para exibição limpa
            for i, row in top_15.iterrows():
                termo = row['Termo em Ascensão']
                col_t, col_l = st.columns([3, 1])
                col_t.write(f"*{i+1}. {termo}*")
                url_ml = f"https://tendencias.mercadolivre.com.br/{urllib.parse.quote(termo)}"
                col_l.markdown(f"[🔎 Ver no ML]({url_ml})")
                st.divider()
        except:
            st.error("Limite de requisições do Google atingido. Tente em 1 minuto.")

# --- ABA 2: COMPARADOR & PROJEÇÃO ---
with tab2:
    st.header("Análise Detalhada de Nicho")
    c1, c2 = st.columns(2)
    t1 = c1.text_input("Produto A", "Game Stick")
    t2 = c2.text_input("Produto B", "Console Retro")

    if t1 and t2:
        pytrends.build_payload([t1, t2], timeframe='today 3-m', geo='BR')
        df = pytrends.interest_over_time()

        if not df.empty:
            df = df.drop(columns=['isPartial'])
            # Lógica de Projeção Simplificada (7 dias)
            for t in [t1, t2]:
                y = df[t].tail(14).values
                slope = np.polyfit(range(14), y, 1)[0]
                future = [max(0, y[-1] + (slope * i)) for i in range(1, 8)]
                df_f = pd.DataFrame(index=pd.date_range(df.index[-1] + pd.Timedelta(days=1), periods=7), data={t: future})
                df = pd.concat([df, df_f])

            fig = px.line(df, title="Tendência e Projeção", color_discrete_sequence=["#FF4B4B", "#1C83E1"])
            fig.add_vline(x=df.index[-8], line_dash="dash", line_color="gray")
            st.plotly_chart(fig, use_container_width=True)
            
            # Palavras Relacionadas para SEO
            st.subheader("💡 Palavras de Apoio para Títulos")
            rel = pytrends.related_queries()
            ca, cb = st.columns(2)
            if t1 in rel and rel[t1]['rising'] is not None:
                ca.write(f"*Subindo para {t1}:*")
                ca.dataframe(rel[t1]['rising'].head(5), use_container_width=True)
            if t2 in rel and rel[t2]['rising'] is not None:
                cb.write(f"*Subindo para {t2}:*")
                cb.dataframe(rel[t2]['rising'].head(5), use_container_width=True)