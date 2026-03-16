import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import requests
from bs4 import BeautifulSoup
from pytrends.request import TrendReq
from datetime import timedelta
from sklearn.linear_model import LinearRegression

# Configuração da Página
st.set_page_config(page_title="Análise de Tendências E-commerce", layout="wide")
st.title("📈 Analisador de Tendências de Produtos")

# --- DICIONÁRIO DE CATEGORIAS ---
CATEGORIAS_ML = {
    "Geral": "https://tendencias.mercadolivre.com.br/",
    "Acessórios para Veículos": "https://tendencias.mercadolivre.com.br/acessorios-para-veiculos",
    "Alimentos e Bebidas": "https://tendencias.mercadolivre.com.br/alimentos-e-bebidas",
    "Beleza e Cuidado Pessoal": "https://tendencias.mercadolivre.com.br/beleza-e-cuidado-pessoal",
    "Brinquedos e Hobbies": "https://tendencias.mercadolivre.com.br/brinquedos-e-hobbies",
    "Calçados, Roupas e Bolsas": "https://tendencias.mercadolivre.com.br/calcados-roupas-e-bolsas",
    "Casa, Móveis e Decoração": "https://tendencias.mercadolivre.com.br/casa-moveis-e-decoracao",
    "Celulares e Telefones": "https://tendencias.mercadolivre.com.br/celulares-e-telefones",
    "Eletrodomésticos": "https://tendencias.mercadolivre.com.br/eletrodomesticos",
    "Eletrônicos, Áudio e Vídeo": "https://tendencias.mercadolivre.com.br/eletronicos-audio-e-video",
    "Esportes e Fitness": "https://tendencias.mercadolivre.com.br/esportes-e-fitness",
    "Ferramentas": "https://tendencias.mercadolivre.com.br/ferramentas",
    "Informática": "https://tendencias.mercadolivre.com.br/informatica",
    "Saúde": "https://tendencias.mercadolivre.com.br/saude",
    "Serviços": "https://tendencias.mercadolivre.com.br/1540-servicos"
}

# --- FUNÇÕES ---

@st.cache_data(ttl=3600)
def obter_tendencias_ml(url):
    """Busca os termos em alta em uma categoria específica do Mercado Livre."""
    headers = {'User-Agent': 'Mozilla/5.0'}
    
    try:
        resposta = requests.get(url, headers=headers)
        soup = BeautifulSoup(resposta.content, 'html.parser')
        
        tendencias = []
        for item in soup.find_all('a'):
            texto = item.get_text(strip=True)
            if texto and len(texto) > 3 and texto not in tendencias:
                tendencias.append(texto)
                
        return tendencias[:10] if tendencias else ["Produto A", "Produto B", "Produto C"]
    except Exception as e:
        st.error(f"Erro ao acessar Mercado Livre: {e}")
        return []

def obter_dados_trends(palavras_chave, periodo='today 6-m'):
    """Busca o volume de pesquisa no Google Trends."""
    pytrends = TrendReq(hl='pt-BR', tz=180)
    try:
        pytrends.build_payload(palavras_chave, cat=0, timeframe=periodo, geo='BR')
        df = pytrends.interest_over_time()
        if not df.empty and 'isPartial' in df.columns:
            df = df.drop(columns=['isPartial'])
        return df
    except Exception as e:
        st.error("Erro ao comunicar com o Google Trends. O limite de requisições pode ter sido atingido.")
        return pd.DataFrame()

def calcular_previsao_e_tendencia(df, dias_previsao=7):
    """Calcula a regressão linear para prever os próximos dias."""
    resultados = {}
    
    for coluna in df.columns:
        y = df[coluna].values
        X = np.arange(len(y)).reshape(-1, 1)
        
        modelo = LinearRegression()
        modelo.fit(X, y)
        
        tendencia_alta = modelo.coef_[0] > 0
        
        X_futuro = np.arange(len(y), len(y) + dias_previsao).reshape(-1, 1)
        previsao = modelo.predict(X_futuro)
        
        ultima_data = df.index[-1]
        datas_futuras = [ultima_data + timedelta(days=i) for i in range(1, dias_previsao + 1)]
        
        resultados[coluna] = {
            'em_alta': tendencia_alta,
            'datas_futuras': datas_futuras,
            'valores_previstos': previsao
        }
        
    return resultados

def plotar_grafico(df_historico, previsoes):
    """Cria um gráfico interativo com Plotly."""
    fig = go.Figure()
    
    for coluna in df_historico.columns:
        fig.add_trace(go.Scatter(
            x=df_historico.index, 
            y=df_historico[coluna],
            mode='lines',
            name=f'{coluna} (Histórico)'
        ))
        
        if coluna in previsoes:
            x_prev = [df_historico.index[-1]] + previsoes[coluna]['datas_futuras']
            y_prev = [df_historico[coluna].iloc[-1]] + list(previsoes[coluna]['valores_previstos'])
            
            fig.add_trace(go.Scatter(
                x=x_prev, 
                y=y_prev,
                mode='lines',
                line=dict(dash='dash'),
                name=f'{coluna} (Previsão 7 dias)'
            ))
            
    fig.update_layout(title="Interesse de Busca ao Longo do Tempo (+ Previsão)",
                      xaxis_title="Data",
                      yaxis_title="Volume de Busca (0-100)",
                      hovermode="x unified")
    return fig

# --- INTERFACE ---

abas = st.tabs(["🔍 Comparação Manual", "🤖 Tendências Mercado Livre"])

# Aba 1: Comparação Manual
with abas[0]:
    st.header("Compare até 3 produtos")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        prod1 = st.text_input("Produto 1", "Placa de Vídeo")
    with col2:
        prod2 = st.text_input("Produto 2", "Processador")
    with col3:
        prod3 = st.text_input("Produto 3", "")
        
    if st.button("Analisar Produtos"):
        produtos_lista = [p for p in [prod1, prod2, prod3] if p.strip() != ""]
        
        if produtos_lista:
            with st.spinner("Buscando dados no Google Trends..."):
                df_trends = obter_dados_trends(produtos_lista)
                
                if not df_trends.empty:
                    previsoes = calcular_previsao_e_tendencia(df_trends)
                    fig = plotar_grafico(df_trends, previsoes)
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.warning("Não foi possível coletar dados para estes termos.")

# Aba 2: Automação Mercado Livre
with abas[1]:
    st.header("Produtos em Alta no Mercado Livre")
    
    # Adicionado o menu suspenso para escolher a categoria (Index 9 = Eletrônicos)
    categoria_selecionada = st.selectbox(
        "Selecione a Categoria para analisar:", 
        list(CATEGORIAS_ML.keys()), 
        index=9
    )
    
    url_categoria = CATEGORIAS_ML[categoria_selecionada]
    
    if st.button(f"Buscar tendências em: {categoria_selecionada}"):
        with st.spinner("Raspando Mercado Livre e cruzando com Google Trends..."):
            termos_ml = obter_tendencias_ml(url_categoria)
            
            if termos_ml:
                st.write(f"**Top 5 termos extraídos:** {', '.join(termos_ml[:5])}")
                
                termos_para_testar = termos_ml[:5] 
                df_ml_trends = obter_dados_trends(termos_para_testar)
                
                if not df_ml_trends.empty:
                    previsoes_ml = calcular_previsao_e_tendencia(df_ml_trends)
                    
                    produtos_em_alta = [p for p in previsoes_ml if previsoes_ml[p]['em_alta']]
                    
                    if produtos_em_alta:
                        st.success(f"🔥 Produtos confirmados em tendência de ALTA: **{', '.join(produtos_em_alta)}**")
                    else:
                        st.info("Nenhum dos produtos extraídos apresenta forte tendência de alta no momento.")
                        
                    fig_ml = plotar_grafico(df_ml_trends, previsoes_ml)
                    st.plotly_chart(fig_ml, use_container_width=True)
