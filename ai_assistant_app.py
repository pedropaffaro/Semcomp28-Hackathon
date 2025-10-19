import streamlit as st
import pandas as pd
import json
import google.generativeai as genai
import re
from dateutil.relativedelta import relativedelta
from dotenv import load_dotenv
import os

load_dotenv()
api_key = os.getenv("API_KEY")

try:
    genai.configure(api_key=api_key)
except Exception:
    print("ERRO: Chave da API do Gemini não configurada. Por favor, edite o arquivo e insira sua chave.")
    exit()

# --- 1. LÓGICA DE PRÉ-PROCESSAMENTO E ANÁLISE (Suas funções originais) ---

# Mantidas as funções carregar_e_preparar_dados, aplicar_filtro_temporal,
# filtrar_gastos_discricionarios, agregar_para_rag, chamar_gemini_com_rag
# exatamente como na última versão que você tem, com as modificações para o contexto rico.

@st.cache_data
def carregar_e_preparar_dados(caminho_arquivo='./dataset/transacoes_bancarias.csv'):
    """Carrega o CSV e faz a preparação inicial."""
    try:
        df = pd.read_csv(caminho_arquivo)
    except FileNotFoundError:
        st.error(f"ERRO: Arquivo '{caminho_arquivo}' não encontrado. Crie o arquivo na mesma pasta do script.")
        return None
    
    df['data'] = pd.to_datetime(df['data'], errors='coerce')
    df['valor'] = pd.to_numeric(df['valor'], errors='coerce')
    df['hora'] = pd.to_datetime(df['hora'], format='%H:%M:%S', errors='coerce').dt.hour
    df['categoria'] = df['categoria'].fillna('Não categorizado')
    df.dropna(subset=['valor', 'hora', 'data'], inplace=True)
    
    df = df.sort_values(by='data')
    return df

def aplicar_filtro_temporal(df_completo, pergunta_usuario):
    """
    Analisa a pergunta do usuário para filtrar o DataFrame principal
    antes de enviar para agregação.
    """
    if df_completo.empty:
        return df_completo

    hoje = df_completo['data'].max()
    pergunta_lower = pergunta_usuario.lower()

    if re.search(r'último mês|ultimos 30 dias|30 dias', pergunta_lower):
        data_inicio = hoje - pd.DateOffset(days=30)
        # st.sidebar.write(f"[Debug] Aplicando filtro: 30 dias (de {data_inicio.date()} até {hoje.date()})")
        return df_completo[df_completo['data'] >= data_inicio]

    if re.search(r'última semana|ultimos 7 dias|7 dias', pergunta_lower):
        data_inicio = hoje - pd.DateOffset(days=7)
        # st.sidebar.write(f"[Debug] Aplicando filtro: 7 dias (de {data_inicio.date()} até {hoje.date()})")
        return df_completo[df_completo['data'] >= data_inicio]

    if re.search(r'mês passado|mes passado', pergunta_lower):
        primeiro_dia_mes_atual = hoje.replace(day=1)
        ultimo_dia_mes_passado = primeiro_dia_mes_atual - pd.DateOffset(days=1)
        primeiro_dia_mes_passado = ultimo_dia_mes_passado.replace(day=1)
        # st.sidebar.write(f"[Debug] Aplicando filtro: Mês passado (de {primeiro_dia_mes_passado.date()} até {ultimo_dia_mes_passado.date()})")
        return df_completo[(df_completo['data'] >= primeiro_dia_mes_passado) & 
                           (df_completo['data'] <= ultimo_dia_mes_passado)]
    
    if re.search(r'este mês|mes atual', pergunta_lower):
        primeiro_dia_mes_atual = hoje.replace(day=1)
        # st.sidebar.write(f"[Debug] Aplicando filtro: Este mês (de {primeiro_dia_mes_atual.date()} até {hoje.date()})")
        return df_completo[df_completo['data'] >= primeiro_dia_mes_atual]

    # st.sidebar.write("[Debug] Nenhum filtro temporal detectado. Usando o dataset completo.")
    return df_completo


def filtrar_gastos_discricionarios(df):
    """
    Filtra o DataFrame para manter apenas gastos "não essenciais" ou "discricionários".
    """
    categorias_essenciais = [
        'educação', 'casa', 'saúde', 'comunicação'
    ]
    valor_limite = 250

    df_discricionario = df[
        (~df['categoria'].str.lower().isin([cat.lower() for cat in categorias_essenciais])) &
        (df['valor'].abs() < valor_limite) &
        (df['valor'] > 0)
    ].copy()
    
    return df_discricionario


def agregar_para_rag(df_discricionario):
    """
    Cria um resumo (dicionário) dos dados para injetar no prompt do RAG.
    """
    if df_discricionario.empty:
        return {
            "periodo_analisado": "Nenhum dado encontrado",
            "resumo": "Nenhum gasto discricionário encontrado para o período solicitado."
        }

    top_5_nomes = df_discricionario['destinatario'].value_counts().nlargest(5).index
    df_top_5 = df_discricionario[df_discricionario['destinatario'].isin(top_5_nomes)]
    gastos_top_5_dict = df_top_5.groupby('destinatario')['valor'].apply(
        lambda x: sorted(x.abs().round(2).tolist(), reverse=True)
    ).to_dict()

    df_discricionario['dia_da_semana'] = df_discricionario['data'].dt.dayofweek
    gastos_uteis = df_discricionario[df_discricionario['dia_da_semana'] < 5]['valor'].abs().sum()
    gastos_fds = df_discricionario[df_discricionario['dia_da_semana'] >= 5]['valor'].abs().sum()
    
    micropagamentos = df_discricionario[df_discricionario['valor'].abs() < 20]
    custo_total_micropagamentos = micropagamentos['valor'].abs().sum()
    quantidade_micropagamentos = len(micropagamentos)

    data_min = df_discricionario['data'].min().strftime('%d/%m/%Y')
    data_max = df_discricionario['data'].max().strftime('%d/%m/%Y')

    insights = {
        "periodo_analisado": f"De {data_min} até {data_max}", 
        "total_gasto_discricionario": f"R$ {df_discricionario['valor'].abs().sum():.2f}",
        "numero_de_transacoes": len(df_discricionario),
        "top_5_destinatarios_com_valores": gastos_top_5_dict, 
        "gastos_por_categoria_discricionaria": df_discricionario.groupby('categoria')['valor'].sum().abs().round(2).sort_values(ascending=False).to_dict(),
        "gastos_de_madrugada": df_discricionario[df_discricionario['hora'].between(0, 5)][['destinatario', 'valor']].to_dict('records'),
        "comparativo_semana": {
            'total_gasto_dias_uteis': f"R$ {gastos_uteis:.2f}",
            'total_gasto_fim_de_semana': f"R$ {gastos_fds:.2f}"
        },
        "custo_micropagamentos": {
            'total_gasto': f"R$ {custo_total_micropagamentos:.2f}",
            'quantidade_de_transacoes': quantidade_micropagamentos
        }
    }
    return insights


def chamar_gemini_com_rag(prompt_usuario, insights, chat_history):
    """Chama o modelo da OpenAI com o contexto dos gastos (RAG)."""
    contexto_str = json.dumps(insights, indent=2, ensure_ascii=False)

    prompt_final = f"""
Você é um assistente virtual especialista em finanças, e está ajudando o usuário pelo WhatsApp.
Seu tom é leve, casual, direto ao ponto.

### Contexto (os dados que você analisou):
{contexto_str}

### Pergunta do usuário:
{prompt_usuario}

### Instruções:
- Seja **MUITO conciso**, como em uma mensagem de WhatsApp.
- Use quebras de linha simples para facilitar a leitura, não parágrafos longos.
- Vá direto aos pontos de economia. Chame os gastos fúteis de "gastos extras".
- Dê exemplos concretos usando `top_5_destinatarios_com_valores`. Se houver muitas transações (ex: 7 no iFood), você pode agrupar: "Vi que foram 7 pedidos no iFood (R$ 50, R$ 45, ...), somando R$ X. Que tal diminuir?"
- **NUNCA** use jargões como "gastos discricionários", "alocação de ativos", etc.
- Sempre termine com uma pergunta rápida e interativa.

### Exemplo de Resposta:
Olá! Dei uma olhada nos seus gastos do último mês.

Reparei em alguns pontos em que podemos melhorar para uma melhor economia:

💡 **Ifood:** Foram 5 pedidos somando R$ 180,50! [R$ 40.50, R$ 35.00, ...]. Que tal focar em cozinhar mais e pedir só 1x na semana? Isso ajudaria a economizar!

💡 **Loja de Jogos:** Vi 3 compras lá [R$ 150, R$ 99, R$ 50]. Elas eram mesmo necessárias?

Só nesses dois pontos, você pode economizar aproximadamente R$ 200 no próximo mês!

Quer que eu veja os micropagamentos?
"""

    modelo = genai.GenerativeModel('models/gemini-2.5-pro') 
    
    if chat_history is None:
        chat = modelo.start_chat(history=[])
    else:
        chat = modelo.start_chat(history=chat_history)

    try:
        resposta = chat.send_message(prompt_final)
        return resposta.text, chat.history
    except Exception as e:
        st.error(f"Ocorreu um erro ao chamar o modelo Gemini: {e}")
        st.info("Verifique se sua chave da API está correta e se há cotas disponíveis.")
        return "Desculpe, não consegui processar sua solicitação no momento.", chat.history

# --- 2. INTERFACE STREAMLIT ---

st.set_page_config(page_title="Assistente Virtual BTG", page_icon="https://play-lh.googleusercontent.com/zR5rx69UH8EaRMeXeZybK5BMga5jWFpbrvC6zPBHAXmXu1Wia8gkx_Pk4r2LSnhKtg")

col1, col2 = st.columns([1, 10], vertical_alignment="bottom") # Proporção da coluna 1 (pequena) para a 2 (grande)

with col1:
    st.image("https://play-lh.googleusercontent.com/zR5rx69UH8EaRMeXeZybK5BMga5jWFpbrvC6zPBHAXmXu1Wia8gkx_Pk4r2LSnhKtg", width=60) # Ajuste o 'width' (largura) conforme necessário

with col2:
    st.title("Assistente Virtual BTG")

st.markdown("Use o chat abaixo para explorar seus padrões de gastos e identificar oportunidades de economia.")

# Carregar os dados uma única vez e armazenar em cache
# Isso é importante para performance, para não recarregar o CSV a cada interação.
if 'df_completo' not in st.session_state:
    st.session_state.df_completo = carregar_e_preparar_dados()
    if st.session_state.df_completo is None:
        st.stop() # Interrompe se o CSV não for encontrado

st.sidebar.header("Informações do Dataset")
st.sidebar.write(f"Transações carregadas: {len(st.session_state.df_completo)} (1 ano)")
st.sidebar.write(f"Período: {st.session_state.df_completo['data'].min().strftime('%d/%m/%Y')} - {st.session_state.df_completo['data'].max().strftime('%d/%m/%Y')}")
st.sidebar.info("A IA vai filtrar os dados com base nas suas perguntas (ex: 'último mês').")

# Inicializa o histórico do chat
if "messages" not in st.session_state:
    st.session_state.messages = []
if "chat_history" not in st.session_state:
    st.session_state.chat_history = None # Para manter o histórico do Gemini

# Exibe mensagens anteriores
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Captura a entrada do usuário
if prompt := st.chat_input("Como posso te ajudar a economizar hoje?"):
    # Adiciona a mensagem do usuário ao histórico
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Analisando seus gastos..."):
            # 1. Filtra o DataFrame com base na pergunta do usuário
            df_contextual = aplicar_filtro_temporal(st.session_state.df_completo, prompt)

            # 2. Filtra apenas os gastos discricionários desse contexto
            df_filtrado = filtrar_gastos_discricionarios(df_contextual)
            
            # 3. Agrega os dados contextuais para o prompt
            insights = agregar_para_rag(df_filtrado)
            
            # 4. Chama o modelo Gemini
            full_response, new_chat_history = chamar_gemini_com_rag(prompt, insights, st.session_state.chat_history)
            st.session_state.chat_history = new_chat_history # Atualiza o histórico do Gemini

            st.markdown(full_response)
    
    # Adiciona a resposta da IA ao histórico do Streamlit
    st.session_state.messages.append({"role": "assistant", "content": full_response})

st.sidebar.markdown("---")
