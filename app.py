import streamlit as st
from pytrends.request import TrendReq
import pandas as pd
import plotly.express as px
import urllib.parse
import numpy as np

# 1. Configuração da Página
st.set_page_config(page_title="Galeria Fácil - Inteligência 360", layout="wide")

# Inicializar Pytrends (Conexão com Google Trends)
try:
    pytrends = TrendReq(hl='pt-BR', tz=360)
except:
    st.error("Erro de conexão com o Google. Recarregue a página em alguns instantes.")

# --- BARRA LATERAL: CALCULADORA DE LUCRO ---
with st.sidebar:
    st.header("🧮 Calculadora de Lucro")
    st.info("Simule a viabilidade real do produto:")
    
    custo = st.number_input("Preço de Custo (R$)", min_value=0.0, value=50.0)
    venda = st.number_input("Preço de Venda (R$)", min_value=0.0, value=120.0)
    
    st.subheader("Taxas e Impostos")
    comissao_pct = st.slider("Comissão Marketplace (%)", 0, 30, 11)
    frete_fixo = st.number_input("Frete/Envio Fixo (R$)", min_value=0.0, value=6.0)
    imposto_pct = st.slider("Imposto sobre Venda (%)", 0, 20, 6)
    
    # Cálculos Financeiros
    vlr_comissao = venda * (comissao_pct / 100)
    vlr_imposto = venda * (imposto_pct / 100)
    lucro_liquido = venda - custo - vlr_comissao - vlr_imposto - frete_fixo
    margem_pct = (lucro_liquido / venda) * 100 if venda > 0 else 0
    
    st.divider()
    st.metric("Lucro Líquido", f"R$ {lucro_liquido:.2f}", delta=f"{margem_pct:.1f}% Margem")
    
    if lucro_liquido < 0:
        st.error("Atenção: Operação com PREJUÍZO!")

# --- NAVEGAÇÃO POR ABAS ---
tab1, tab2 = st.tabs(["🏆 Top 15 Oportunidades", "⚖️ Comparador & Projeção"])

# --- ABA 1: TOP 15 PRODUTOS EM ALTA ---
with tab1:
    st.header("🔥 Tendências de Busca no Brasil (Últimas 24h)")
    st.write("Estes são os termos com maior crescimento súbito de interesse.")
    
    if st.button("🔄 Atualizar Lista de Oportunidades"):
        try:
            # Busca as tendências diárias do Google Brasil
            df_trending = pytrends.trending_searches(pn='brazil')
            top_15 = df_trending.head(15)
            top_15.columns = ['Termo em Ascensão']
            
            for i, row in top_15.iterrows():
                termo = row['Termo em Ascensão']
                col_t, col_l = st.columns([3, 1])
                col_t.subheader(f"{i+1}. {termo}")
                
                # Link dinâmico para o Mercado Livre Tendências
                url_ml = f"https://tendencias.mercadolivre.com.br/{urllib.parse.quote(termo)}"
                col_l.markdown(f"### [🔎 Ver no ML]({url_ml})")
                st.divider()
        except:
            st.warning("O Google limitou o acesso temporariamente. Tente novamente em 2 minutos.")

# --- ABA 2: COMPARADOR E PROJEÇÃO PREDITIVA ---
with tab2:
    st.header("🔍 Análise de Nicho e Previsão")
    c1, c2 = st.columns(2)
    
    termo_a = c1.text_input("Produto A", "Game Stick")
    termo_b = c2.text_input("Produto B", "Console Retro")

    if termo_a and termo_b:
        with st.spinner("Analisando dados históricos e projetando futuro..."):
            # Busca dados dos últimos 3 meses
            pytrends.build_payload([termo_a, termo_b], timeframe='today 3-m', geo='BR')
            df_hist = pytrends.interest_over_time()

            if not df_hist.empty:
                df_hist = df_hist.drop(columns=['isPartial'])
                
                # --- LÓGICA DE PROJEÇÃO (7 DIAS) ---
                for t in [termo_a, termo_b]:
                    y_vals = df_hist[t].tail(14).values
                    x_vals = np.arange(14)
                    slope = np.polyfit(x_vals, y_vals, 1)[0] # Tendência linear
                    
                    # Datas futuras
                    last_date = df_hist.index[-1]
                    future_dates = pd.date_range(last_date + pd.Timedelta(days=1), periods=7)
                    
                    # Valores projetados
                    future_vals = [max(0, y_vals[-1] + (slope * i)) for i in range(1, 8)]
                    df_proj = pd.DataFrame(index=future_dates, data={t: future_vals})
                    df_hist = pd.concat([df_hist, df_proj])

                # Gráfico Interativo
                fig = px.line(df_hist, title="Interesse Histórico + Projeção (Próximos 7 dias)",
                              labels={'value': 'Popularidade (0-100)', 'index': 'Data'},
                              color_discrete_map={termo_a: "#FF4B4B", termo_b: "#1C83E1"})
                
                # Linha divisória entre passado e futuro
                fig.add_vline(x=last_date, line_dash="dash", line_color="gray", annotation_text="Hoje")
                st.plotly_chart(fig, use_container_width=True)
                
                # --- SEÇÃO DE SEO (PALAVRAS RELACIONADAS) ---
                st.divider()
                st.subheader("💡 Palavras-Chave em Ascensão (Use no Título do Anúncio)")
                rel_queries = pytrends.related_queries()
                
                col_seo_a, col_seo_b = st.columns(2)
                
                with col_seo_a:
                    st.write(f"*Relacionadas a {termo_a}:*")
                    if termo_a in rel_queries and rel_queries[termo_a]['rising'] is not None:
                        st.dataframe(rel_queries[termo_a]['rising'].head(5), use_container_width=True)
                    else:
                        st.info("Sem dados de subida recente.")

                with col_seo_b:
                    st.write(f"*Relacionadas a {termo_b}:*")
                    if termo_b in rel_queries and rel_queries[termo_b]['rising'] is not None:
                        st.dataframe(rel_queries[termo_b]['rising'].head(5), use_container_width=True)
                    else:
                        st.info("Sem dados de subida recente.")
            else:
                st.warning("Não há dados suficientes para esses termos no período.")

st.caption("Desenvolvido para Galeria Fácil - Inteligência de Mercado 2026")