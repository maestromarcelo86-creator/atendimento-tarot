python
import streamlit as st
import time
import mercadopago
import stripe
from supabase import create_client
from streamlit_autorefresh import st_autorefresh

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(
    page_title="Templo de Tarot & Vidência | Consulta Online",
    page_icon="🔮",
    layout="centered",
    initial_sidebar_state="collapsed"
)

PRECO_MINUTO = 3.99

# --- ESTILO VISUAL PERSONALIZADO (TEMA MÍSTICO DARK & DOURADO) ---
st.markdown("""
<style>
    /* Fundo principal e textos */
    .stApp {
        background: linear-gradient(180deg, #120924 0%, #1d1035 50%, #0e071c 100%);
        color: #f3e8ff;
    }
    h1, h2, h3 {
        color: #f5d061 !important;
        font-family: 'Georgia', serif;
    }
    /* Banner Principal */
    .hero-box {
        background: rgba(255, 255, 255, 0.05);
        border: 1px solid rgba(245, 208, 97, 0.35);
        border-radius: 16px;
        padding: 24px;
        text-align: center;
        margin-bottom: 20px;
    }
    .status-badge-on {
        background-color: rgba(16, 185, 129, 0.2);
        color: #6ee7b7;
        border: 1px solid #10b981;
        padding: 5px 14px;
        border-radius: 20px;
        font-weight: bold;
        display: inline-block;
        margin-bottom: 10px;
    }
    .status-badge-off {
        background-color: rgba(239, 68, 68, 0.2);
        color: #fca5a5;
        border: 1px solid #ef4444;
        padding: 5px 14px;
        border-radius: 20px;
        font-weight: bold;
        display: inline-block;
        margin-bottom: 10px;
    }
    /* Cronômetro em Destaque */
    .timer-box {
        background: linear-gradient(90deg, #3b1d6e 0%, #5829a7 100%);
        border: 2px solid #f5d061;
        border-radius: 12px;
        padding: 15px;
        text-align: center;
        font-size: 24px;
        font-weight: bold;
        color: #ffffff;
        margin-bottom: 16px;
    }
    /* Cards de Pacotes */
    .pkg-card {
        background: rgba(255, 255, 255, 0.04);
        border: 1px solid rgba(245, 208, 97, 0.25);
        border-radius: 12px;
        padding: 16px;
        text-align: center;
        margin-bottom: 10px;
    }
    /* Botões */
    .stButton>button {
        background: linear-gradient(90deg, #d4af37 0%, #f5d061 100%);
        color: #120924 !important;
        font-weight: bold;
        border: none;
        border-radius: 10px;
        padding: 10px 20px;
        width: 100%;
    }
    .stButton>button:hover {
        opacity: 0.9;
    }
</style>
""", unsafe_allow_html=True)

# --- CONEXÃO COM SUPABASE (MANTIDA) ---
@st.cache_resource
def init_supabase():
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

supabase = init_supabase()

def get_sessao():
    try:
        res = supabase.table("sessao_tarot").select("*").eq("id", 1).execute()
        if not res.data:
            dados_iniciais = {"id": 1, "segundos_restantes": 0, "ultimo_tick": 0, "tarologo_online": True}
            supabase.table("sessao_tarot").insert(dados_iniciais).execute()
            return dados_iniciais
        return res.data
    except Exception as e:
        st.error(f"Erro de conexão: {e}")
        st.stop()

sessao = get_sessao()
agora = int(time.time())
segundos_restantes = sessao["segundos_restantes"]

# Cronômetro ao vivo
if segundos_restantes > 0:
    st_autorefresh(interval=5000, key="cronometro_ao_vivo")
    decorrido = agora - sessao["ultimo_tick"]
    if decorrido >= 5:
        novo_tempo = max(0, segundos_restantes - decorrido)
        supabase.table("sessao_tarot").update({
            "segundos_restantes": novo_tempo,
            "ultimo_tick": agora
        }).eq("id", 1).execute()
        segundos_restantes = novo_tempo

# --- PAINEL DO TARÓLOGO (BARRA LATERAL OCULTA) ---
eh_tarologo = False
with st.sidebar:
    st.header("🔮 Painel do Tarólogo")
    senha = st.text_input("Senha de Acesso", type="password")
    if senha == st.secrets.get("SENHA_TAROLOGO", "1760"):
        eh_tarologo = True
        st.success("Conectado como Tarólogo")
        online = st.toggle("Status Online no Site", value=sessao["tarologo_online"])
        if online != sessao["tarologo_online"]:
            supabase.table("sessao_tarot").update({"tarologo_online": online}).eq("id", 1).execute()
            st.rerun()

        st.divider()
        st.subheader("⏱️ Gerenciar Tempo")
        mins_manual = st.number_input("Adicionar minutos:", min_value=1, value=10)
        if st.button("✅ Liberar / Somar Minutos"):
            novo_saldo = segundos_restantes + (mins_manual * 60)
            supabase.table("sessao_tarot").update({
                "segundos_restantes": novo_saldo,
                "ultimo_tick": int(time.time())
            }).eq("id", 1).execute()
            st.rerun()

        if st.button("⏹️ Encerrar Consulta"):
            supabase.table("sessao_tarot").update({"segundos_restantes": 0}).eq("id", 1).execute()
            st.rerun()

        if st.button("🗑️ Limpar Conversa"):
            supabase.table("mensagens_tarot").delete().neq("id", 0).execute()
            st.rerun()

# --- 1. CABEÇALHO DO SITE (HERO SECTION) ---
badge = '<span class="status-badge-on">🟢 ONLINE PARA ATENDIMENTO AGORA</span>' if sessao["tarologo_online"] else '<span class="status-badge-off">🔴 EM ATENDIMENTO / OFFLINE</span>'

st.markdown(f"""
<div class="hero-box">
    {badge}
    <h1>🔮 Consulta Espiritual & Tarot</h1>
    <p style="font-size: 17px; color: #e2d4f0;">
        Orientação espiritual, amorosa e financeira com tiragem de cartas ao vivo.<br>
        Atendimento sigiloso por <b>Chat</b> ou <b>Chamada de Vídeo</b> • <b>R$ {PRECO_MINUTO:.2f} / minuto</b>
    </p>
</div>
""", unsafe_allow_html=True)

# --- 2. SALA DE CONSULTA AO VIVO (SE HOUVER MINUTOS) ---
if segundos_restantes > 0:
    mins = segundos_restantes // 60
    segs = segundos_restantes % 60
    st.markdown(f'<div class="timer-box">⏳ Tempo Disponível na Sala: {mins:02d}:{segs:02d}</div>', unsafe_allow_html=True)

    aba_chat, aba_video = st.tabs(["💬 Sala de Chat ao Vivo", "📹 Sala de Vídeo ao Vivo"])

    with aba_chat:
        msgs = supabase.table("mensagens_tarot").select("*").order("id").execute().data
        if not msgs:
            st.caption("A sala está aberta. Envie sua pergunta ou nome completo e data de nascimento para iniciar a tiragem.")
        for m in msgs:
            with st.chat_message(m["autor"], avatar="🔮" if m["autor"] == "assistant" else "👤"):
                st.write(m["texto"])

        novo_texto = st.chat_input("Escreva sua mensagem aqui...")
        if novo_texto:
            autor = "assistant" if eh_tarologo else "user"
            supabase.table("mensagens_tarot").insert({"autor": autor, "texto": novo_texto}).execute()
            st.rerun()

    with aba_video:
        st.info("Permita o acesso à câmera e microfone no navegador e clique em **Entrar na reunião**.")
        st.components.v1.iframe("https://jit.si", height=520)

    st.divider()

# --- 3. ESCOLHA DE PACOTES E PAGAMENTO ---
st.subheader("✨ Escolha o Tempo da sua Consulta")

c1, c2, c3 = st.columns(3)
with c1:
    st.markdown(f'<div class="pkg-card"><h4>🌙 Consulta Rápida</h4><h3>10 Minutos</h3><p>R$ {10*PRECO_MINUTO:.2f}</p></div>', unsafe_allow_html=True)
with c2:
    st.markdown(f'<div class="pkg-card"><h4>⭐ Mais Escolhido</h4><h3>20 Minutos</h3><p>R$ {20*PRECO_MINUTO:.2f}</p></div>', unsafe_allow_html=True)
with c3:
    st.markdown(f'<div class="pkg-card"><h4>👑 Tiragem Completa</h4><h3>30 Minutos</h3><p>R$ {30*PRECO_MINUTO:.2f}</p></div>', unsafe_allow_html=True)

col_sel, col_val = st.columns(2)
with col_sel:
    minutos_escolhidos = st.selectbox("Selecione a duração desejada:",, index=1)
with col_val:
    valor_total = round(minutos_escolhidos * PRECO_MINUTO, 2)
    st.metric("Investimento Total", f"R$ {valor_total:.2f}")

forma_pagto = st.radio(
    "Selecione como deseja pagar:",
    [
        "💠 Mercado Pago (Pix na hora, Crédito ou Débito)",
        "💳 Stripe (Cartão de Crédito Nacional / Internacional)",
        "🏦 Depósito / Transferência Bancária"
    ]
)

if forma_pagto == "💠 Mercado Pago (Pix na hora, Crédito ou Débito)":
    if st.button("Gerar Link de Pagamento (Pix / Cartão)"):
        sdk = mercadopago.SDK(st.secrets["MP_ACCESS_TOKEN"])
        preferencia = {
            "items": [{
                "title": f"Consulta Tarot - {minutos_escolhidos} minutos",
                "quantity": 1,
                "currency_id": "BRL",
                "unit_price": float(valor_total)
            }],
            "payment_methods": {"installments": 6}
        }
        res = sdk.preference().create(preferencia)
        if "init_point" in res["response"]:
            st.session_state.mp_pref_id = res["response"]["id"]
            st.link_button("👉 Abrir Tela Segura do Mercado Pago", res["response"]["init_point"])
            st.caption("Após concluir o pagamento, volte aqui e clique no botão de confirmação abaixo.")
        else:
            st.error("Não foi possível gerar o pagamento. Verifique as credenciais.")

    if "mp_pref_id" in st.session_state:
        if st.button("✅ Já realizei o pagamento (Liberar Sala)"):
            sdk = mercadopago.SDK(st.secrets["MP_ACCESS_TOKEN"])
            busca = sdk.payment().search({"sort": "date_created", "criteria": "desc", "limit": 5})
            aprovado = False
            for p in busca["response"].get("results", []):
                if p.get("status") == "approved" and float(p.get("transaction_amount", 0)) == float(valor_total):
                    if st.session_state.get("ultimo_pgto_liberado") != p["id"]:
                        st.session_state.ultimo_pgto_liberado = p["id"]
                        aprovado = True
                        break
            if aprovado:
                novo_saldo = segundos_restantes + (minutos_escolhidos * 60)
                supabase.table("sessao_tarot").update({
                    "segundos_restantes": novo_saldo,
"ultimo_tick": int(time.time())
}).eq("id", 1).execute()
st.success("Pagamento aprovado! Sua sala foi liberada acima.")
st.rerun()
else:
st.warning("Ainda aguardando a confirmação do banco. Aguarde 5 segundos e clique novamente.")
elif forma_pagto == "💳 Stripe (Cartão de Crédito Nacional / Internacional)":
if st.button("Gerar Checkout no Cartão (Stripe)"):
stripe.api_key = st.secrets["STRIPE_SECRET_KEY"]
sessao_stripe = stripe.checkout.Session.create(
payment_method_types=["card"],
line_items=[{
"price_data": {
"currency": "brl",
"product_data": {"name": f"Consulta Tarot ({minutos_escolhidos} min)"},
"unit_amount": int(valor_total * 100),
},
"quantity": 1,
}],
mode="payment",
success_url="streamlit.io",
cancel_url="streamlit.io",
)
st.session_state.stripe_session_id = sessao_stripe.id
st.link_button("👉 Pagar com Cartão no Stripe", sessao_stripe.url)
if "stripe_session_id" in st.session_state:
if st.button("✅ Já paguei no Stripe (Liberar Sala)"):
stripe.api_key = st.secrets["STRIPE_SECRET_KEY"]
check = stripe.checkout.Session.retrieve(st.session_state.stripe_session_id)
if check.payment_status == "paid":
novo_saldo = segundos_restantes + (minutos_escolhidos * 60)
supabase.table("sessao_tarot").update({
"segundos_restantes": novo_saldo,
"ultimo_tick": int(time.time())
}).eq("id", 1).execute()
del st.session_state.stripe_session_id
st.rerun()
else:
st.warning("Pagamento ainda não confirmado pelo cartão.")
elif forma_pagto == "🏦 Depósito / Transferência Bancária":
st.info("""
Dados para Depósito ou Transferência (TED/DOC):
* Banco: Seu Banco (ex: Nubank / Itaú / Caixa)
* Agência: 0001 • Conta: 123456-7
* Favorecido: Seu Nome Completo
""")
comprovante = st.file_uploader("Envie o comprovante (foto ou PDF):", type=["png", "jpg", "jpeg", "pdf"])
if comprovante:
st.success("Comprovante enviado! O tarólogo irá validar e liberar seu tempo na sala.")

--- 4. RODAPÉ INFORMATIVO ---

st.divider()
col_info1, col_info2 = st.columns(2)
with col_info1:
st.markdown("🔒 Atendimento 100% Sigiloso\n\nSuas perguntas e tiragens são privadas e o histórico pode ser apagado ao final da sessão.")
with col_info2:
st.markdown("⏳ Como funciona o tempo?\n\nO cronômetro só começa a contar após a confirmação do pagamento e você pode recarregar minutos a qualquer momento.")
