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

# --- FUNÇÕES ---

@st.cache_data(ttl=3600) # Cache de 1 hora
def obter_tendencias_ml():
    """Busca os termos em alta no Mercado Livre."""
    url = "https://tendencias.mercadolivre.com.br/"
    headers = {'User-Agent': 'Mozilla/5.0'}
    
    try:
        resposta = requests.get(url, headers=headers)
        soup = BeautifulSoup(resposta.content, 'html.parser')
        
        tendencias = []
        # O Mercado Livre costuma listar as buscas em tags <a> com classes específicas
        # Vamos buscar links gerais que pareçam pesquisas para manter o código resiliente
        for item in soup.find_all('a'):
            texto = item.get_text(strip=True)
            # Filtra links vazios ou curtos e evita duplicatas
            if texto and len(texto) > 3 and texto not in tendencias:
                tendencias.append(texto)
                
        # Retorna apenas os 10 primeiros para evitar bloqueios no Google Trends
        return tendencias[:10] if tendencias else ["Fones de ouvido", "Smartwatch", "Tênis esportivo"]
    except Exception as e:
        st.error(f"Erro ao acessar Mercado Livre: {e}")
        return []

def obter_dados_trends(palavras_chave, periodo='today 6-m'):
    """Busca o volume de pesquisa no Google Trends."""
    pytrends = TrendReq(hl='pt-BR', tz=180) # Fuso horário do Brasil
    try:
        pytrends.build_payload(palavras_chave, cat=0, timeframe=periodo, geo='BR')
        df = pytrends.interest_over_time()
        if not df.empty and 'isPartial' in df.columns:
            df = df.drop(columns=['isPartial'])
        return df
    except Exception as e:
        st.error("Erro ao comunicar com o Google Trends. Tente novamente mais tarde (limite de requisições).")
        return pd.DataFrame()

def calcular_previsao_e_tendencia(df, dias_previsao=7):
    """Calcula a regressão linear para prever os próximos dias e detectar tendência de alta."""
    resultados = {}
    
    for coluna in df.columns:
        # Preparar dados para o modelo
        y = df[coluna].values
        X = np.arange(len(y)).reshape(-1, 1)
        
        modelo = LinearRegression()
        modelo.fit(X, y)
        
        # A inclinação da reta (coeficiente) indica se a tendência é de alta (> 0) ou baixa (< 0)
        tendencia_alta = modelo.coef_[0] > 0
        
        # Prever os próximos dias
        X_futuro = np.arange(len(y), len(y) + dias_previsao).reshape(-1, 1)
        previsao = modelo.predict(X_futuro)
        
        # Criar datas futuras
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
        # Linha histórica
        fig.add_trace(go.Scatter(
            x=df_historico.index, 
            y=df_historico[coluna],
            mode='lines',
            name=f'{coluna} (Histórico)'
        ))
        
        # Linha de previsão (tracejada)
        if coluna in previsoes:
            # Conecta o último ponto histórico com o primeiro ponto da previsão
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
        prod1 = st.text_input("Produto 1", "iPhone 15")
    with col2:
        prod2 = st.text_input("Produto 2", "Samsung S24")
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
    st.write("Buscando tendências e cruzando com o histórico de 6 meses do Google Trends.")
    
    if st.button("Buscar e Analisar"):
        with st.spinner("Raspando Mercado Livre e cruzando com Google Trends..."):
            termos_ml = obter_tendencias_ml()
            
            if termos_ml:
                st.write(f"**Termos encontrados:** {', '.join(termos_ml)}")
                
                # O Google Trends permite até 5 palavras por vez. Vamos testar os 5 primeiros.
                termos_para_testar = termos_ml[:5] 
                df_ml_trends = obter_dados_trends(termos_para_testar)
                
                if not df_ml_trends.empty:
                    previsoes_ml = calcular_previsao_e_tendencia(df_ml_trends)
                    
                    produtos_em_alta = [p for p in previsoes_ml if previsoes_ml[p]['em_alta']]
                    
                    if produtos_em_alta:
                        st.success(f"🔥 Produtos confirmados em tendência de ALTA no Google Trends: **{', '.join(produtos_em_alta)}**")
                    else:
                        st.info("Nenhum dos produtos extraídos apresenta forte tendência de alta no momento.")
                        
                    fig_ml = plotar_grafico(df_ml_trends, previsoes_ml)
                    st.plotly_chart(fig_ml, use_container_width=True)