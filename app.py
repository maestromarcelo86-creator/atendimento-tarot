import streamlit as st
import time
import mercadopago
import stripe
from supabase import create_client
from streamlit_autorefresh import st_autorefresh

st.set_page_config(
    page_title="Marcelo Astrologo | Tarot, Vidência, Astrologia & Consultoria Espiritual",
    page_icon="🔮",
    layout="centered",
    initial_sidebar_state="collapsed"
)

PRECO_MINUTO = 3.99

st.markdown("""
<style>
    .stApp {
        background: linear-gradient(180deg, #120924 0%, #1d1035 50%, #0e071c 100%);
        color: #f3e8ff;
    }
    h1, h2, h3, h4 {
        color: #f5d061 !important;
        font-family: 'Georgia', serif;
    }
    .hero-box {
        background: rgba(255, 255, 255, 0.05);
        border: 1px solid rgba(245, 208, 97, 0.4);
        border-radius: 18px;
        padding: 28px 22px;
        text-align: center;
        margin-bottom: 22px;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.35);
    }
    .subtitle-gold {
        color: #f5d061;
        font-size: 15px;
        letter-spacing: 1.5px;
        text-transform: uppercase;
        font-weight: bold;
        margin-bottom: 8px;
    }
    .status-badge-on {
        background-color: rgba(16, 185, 129, 0.2);
        color: #6ee7b7;
        border: 1px solid #10b981;
        padding: 6px 16px;
        border-radius: 20px;
        font-weight: bold;
        font-size: 13px;
        display: inline-block;
        margin-bottom: 14px;
    }
    .status-badge-off {
        background-color: rgba(239, 68, 68, 0.2);
        color: #fca5a5;
        border: 1px solid #ef4444;
        padding: 6px 16px;
        border-radius: 20px;
        font-weight: bold;
        font-size: 13px;
        display: inline-block;
        margin-bottom: 14px;
    }
    .timer-box {
        background: linear-gradient(90deg, #3b1d6e 0%, #5829a7 100%);
        border: 2px solid #f5d061;
        border-radius: 12px;
        padding: 16px;
        text-align: center;
        font-size: 24px;
        font-weight: bold;
        color: #ffffff;
        margin-bottom: 18px;
    }
    .spec-card {
        background: rgba(255, 255, 255, 0.04);
        border: 1px solid rgba(245, 208, 97, 0.25);
        border-radius: 12px;
        padding: 16px;
        text-align: center;
        min-height: 150px;
        margin-bottom: 12px;
    }
    .pkg-card {
        background: rgba(245, 208, 97, 0.07);
        border: 1px solid rgba(245, 208, 97, 0.35);
        border-radius: 12px;
        padding: 16px;
        text-align: center;
        margin-bottom: 10px;
    }
    .stButton>button {
        background: linear-gradient(90deg, #d4af37 0%, #f5d061 100%);
        color: #120924 !important;
        font-weight: bold;
        border: none;
        border-radius: 10px;
        padding: 12px 20px;
        width: 100%;
    }
    .stButton>button:hover {
        opacity: 0.92;
    }
</style>
""", unsafe_allow_html=True)

@st.cache_resource
def init_supabase():
    return create_client(st.secrets.get("SUPABASE_URL"), st.secrets.get("SUPABASE_KEY"))

supabase = init_supabase()

def get_sessao():
    try:
        res = supabase.table("sessao_tarot").select("*").eq("id", 1).execute()
        if not res.data:
            dados_iniciais = {"id": 1, "segundos_restantes": 0, "ultimo_tick": 0, "tarologo_online": True}
            supabase.table("sessao_tarot").insert(dados_iniciais).execute()
            return dados_iniciais
        return list(res.data).pop(0)
    except Exception as e:
        st.error(f"Erro de conexão com o banco: {e}")
        st.stop()

sessao = get_sessao()
agora = int(time.time())
segundos_restantes = sessao.get("segundos_restantes", 0)

if segundos_restantes > 0:
    st_autorefresh(interval=5000, key="cronometro_ao_vivo")
    decorrido = agora - sessao.get("ultimo_tick", agora)
    if decorrido >= 5:
        novo_tempo = max(0, segundos_restantes - decorrido)
        supabase.table("sessao_tarot").update({
            "segundos_restantes": novo_tempo,
            "ultimo_tick": agora
        }).eq("id", 1).execute()
        segundos_restantes = novo_tempo

eh_tarologo = False
with st.sidebar:
    st.header("🔮 Painel - Marcelo Astrologo")
    senha = st.text_input("Senha de Administrador", type="password")
    if senha == st.secrets.get("SENHA_TAROLOGO", "1760"):
        eh_tarologo = True
        st.success("Painel Administrativo Liberado")
        online = st.toggle("Status Online no Site", value=sessao.get("tarologo_online", True))
        if online != sessao.get("tarologo_online", True):
            supabase.table("sessao_tarot").update({"tarologo_online": online}).eq("id", 1).execute()
            st.rerun()

        st.divider()
        st.subheader("⏱️ Controle de Atendimento")
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

        if st.button("🗑️ Limpar Histórico do Chat"):
            supabase.table("mensagens_tarot").delete().neq("id", 0).execute()
            st.rerun()

badge = '<span class="status-badge-on">🟢 DISPONÍVEL PARA CONSULTA AO VIVO</span>' if sessao.get("tarologo_online", True) else '<span class="status-badge-off">🔴 EM ATENDIMENTO / OFFLINE</span>'

st.markdown(f"""
<div class="hero-box">
    {badge}
    <div class="subtitle-gold">Tarólogo • Espírita Vidente • Astrólogo</div>
    <h1>🔮 Marcelo Astrologo</h1>
    <p style="font-size: 16px; color: #e2d4f0; line-height: 1.6;">
        Consultoria espiritual completa, tiragem de Tarot, vidência espírita, Astrologia e leitura de Mapa Astral.<br>
        Atendimento individual e sigiloso por <b>Chat</b> ou <b>Vídeo</b> • <b>R$ {PRECO_MINUTO:.2f} / minuto</b>
    </p>
</div>
""", unsafe_allow_html=True)

if segundos_restantes > 0:
    mins = segundos_restantes // 60
    segs = segundos_restantes % 60
    st.markdown(f'<div class="timer-box">⏳ Tempo Restante na Consulta: {mins:02d}:{segs:02d}</div>', unsafe_allow_html=True)

    aba_chat, aba_video = st.tabs(("💬 Atendimento por Chat ao Vivo", "📹 Atendimento por Vídeo ao Vivo"))

    with aba_chat:
        msgs = supabase.table("mensagens_tarot").select("*").order("id").execute().data
        if not msgs:
            st.caption("Bem-vindo(a) à sala de consulta com Marcelo Astrologo. Informe seu nome completo, data de nascimento e sua questão para começarmos.")
        for m in msgs:
            autor_msg = m.get("autor", "user")
            with st.chat_message(autor_msg, avatar="🔮" if autor_msg == "assistant" else "👤"):
                st.write(m.get("texto", ""))

        novo_texto = st.chat_input("Digite sua mensagem ou pergunta...")
        if novo_texto:
            autor = "assistant" if eh_tarologo else "user"
            supabase.table("mensagens_tarot").insert({"autor": autor, "texto": novo_texto}).execute()
            st.rerun()

    with aba_video:
        st.info("Autorize o uso da câmera e microfone no navegador e clique em **Entrar na reunião** para falar ao vivo.")
        st.components.v1.iframe("https://jit.si", height=520)

    st.divider()

st.subheader("✨ Áreas de Atendimento & Consultoria")
e1, e2, e3 = st.columns(3)
with e1:
    st.markdown('<div class="spec-card"><h4>🃏 Tarot & Vidência</h4><p style="font-size:14px;">Respostas diretas sobre amor, caminhos financeiros, decisões e revelações espirituais.</p></div>', unsafe_allow_html=True)
with e2:
    st.markdown('<div class="spec-card"><h4>🌌 Astrologia & Mapa Astral</h4><p style="font-size:14px;">Análise do seu mapa natal, trânsitos astrológicos, sinastria amorosa e ciclos de vida.</p></div>', unsafe_allow_html=True)
with e3:
    st.markdown('<div class="spec-card"><h4>🕊️ Consultoria Espiritual</h4><p style="font-size:14px;">Orientação espírita, limpeza energética, proteção e direcionamento para o mundo espiritual.</p></div>', unsafe_allow_html=True)

st.divider()

st.subheader("⏱️ Escolha o Tempo da sua Consulta")

c1, c2, c3 = st.columns(3)
with c1:
    st.markdown(f'<div class="pkg-card"><h4>🌙 Consulta Objetiva</h4><h3>10 Minutos</h3><p>R$ {10*PRECO_MINUTO:.2f}</p></div>', unsafe_allow_html=True)
with c2:
    st.markdown(f'<div class="pkg-card"><h4>⭐ Mais Escolhido</h4><h3>20 Minutos</h3><p>R$ {20*PRECO_MINUTO:.2f}</p></div>', unsafe_allow_html=True)
with c3:
    st.markdown(f'<div class="pkg-card"><h4>👑 Mapa & Leitura Completa</h4><h3>30 Minutos</h3><p>R$ {30*PRECO_MINUTO:.2f}</p></div>', unsafe_allow_html=True)

col_sel, col_val = st.columns(2)
with col_sel:
    minutos_escolhidos = st.selectbox("Selecione a duração desejada:", (5, 10, 15, 20, 30, 45, 60), index=1)
with col_val:
    valor_total = round(minutos_escolhidos * PRECO_MINUTO, 2)
    st.metric("Valor Total da Sessão", f"R$ {valor_total:.2f}")

forma_pagto = st.radio(
    "Escolha a forma de pagamento:",
    (
        "💠 Mercado Pago (Pix na hora, Crédito ou Débito)",
        "💳 Stripe (Cartão de Crédito Nacional / Internacional)",
        "🏦 Depósito / Transferência Bancária"
    )
)

if forma_pagto == "💠 Mercado Pago (Pix na hora, Crédito ou Débito)":
    if st.button("Gerar Link de Pagamento (Pix / Cartão)"):
        sdk = mercadopago.SDK(st.secrets.get("MP_ACCESS_TOKEN"))
        item_mp = {
            "title": f"Consulta Marcelo Astrologo - {minutos_escolhidos} min",
            "quantity": 1,
            "currency_id": "BRL",
            "unit_price": float(valor_total)
        }
        preferencia = {
            "items": list((item_mp,)),
            "payment_methods": {"installments": 6}
        }
res = sdk.preference().create(preferencia)
resp_mp = res.get("response", {})
if "init_point" in resp_mp:
st.session_state.mp_pref_id = resp_mp.get("id")
st.link_button("👉 Abrir Pagamento Seguro (Mercado Pago)", resp_mp.get("init_point"))
st.caption("Após concluir o pagamento, clique no botão de confirmação abaixo para liberar sua sala.")
else:
st.error("Não foi possível gerar o link. Verifique suas credenciais do Mercado Pago.")
if "mp_pref_id" in st.session_state:
if st.button("✅ Já realizei o pagamento (Liberar Sala)"):
sdk = mercadopago.SDK(st.secrets.get("MP_ACCESS_TOKEN"))
busca = sdk.payment().search({"sort": "date_created", "criteria": "desc", "limit": 5})
aprovado = False
resultados = busca.get("response", {}).get("results", ())
for p in resultados:
if p.get("status") == "approved" and float(p.get("transaction_amount", 0)) == float(valor_total):
if st.session_state.get("ultimo_pgto_liberado") != p.get("id"):
st.session_state.ultimo_pgto_liberado = p.get("id")
aprovado = True
break
if aprovado:
novo_saldo = segundos_restantes + (minutos_escolhidos * 60)
supabase.table("sessao_tarot").update({
"segundos_restantes": novo_saldo,
"ultimo_tick": int(time.time())
}).eq("id", 1).execute()
st.success("Pagamento confirmado! Sua sala de consulta foi liberada acima.")
st.rerun()
else:
st.warning("Aguardando confirmação do pagamento. Aguarde 5 segundos e clique novamente.")
elif forma_pagto == "💳 Stripe (Cartão de Crédito Nacional / Internacional)":
if st.button("Gerar Link no Cartão (Stripe)"):
stripe.api_key = st.secrets.get("STRIPE_SECRET_KEY")
item_stripe = {
"price_data": {
"currency": "brl",
"product_data": {"name": f"Consulta Marcelo Astrologo ({minutos_escolhidos} min)"},
"unit_amount": int(valor_total * 100),
},
"quantity": 1,
}
sessao_stripe = stripe.checkout.Session.create(
payment_method_types=list(("card",)),
line_items=list((item_stripe,)),
mode="payment",
success_url="streamlit.io",
cancel_url="streamlit.io",
)
st.session_state.stripe_session_id = sessao_stripe.id
st.link_button("👉 Pagar com Cartão no Stripe", sessao_stripe.url)
if "stripe_session_id" in st.session_state:
if st.button("✅ Já paguei no Stripe (Liberar Sala)"):
stripe.api_key = st.secrets.get("STRIPE_SECRET_KEY")
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
Dados Bancários para Depósito ou Transferência (TED/DOC):
* Banco: Banco Safra (Código 422)
* Agência: 0115
* Conta Corrente: 342955-9
* Favorecido: Marcelo Astrologo
""")
comprovante = st.file_uploader("Anexe o comprovante (foto ou PDF):", type=list(("png", "jpg", "jpeg", "pdf")))
if comprovante:
st.success("Comprovante enviado! Marcelo Astrologo irá validar e liberar seus minutos na sala.")
st.divider()
col_info1, col_info2 = st.columns(2)
with col_info1:
st.markdown("🔒 Sigilo Absoluto\n\nTodas as consultas de Tarot, Vidência e Mapa Astral com Marcelo Astrologo são 100% confidenciais.")
with col_info2:
st.markdown("⏳ Tempo Transparente\n\nO cronômetro inicia apenas após a confirmação do pagamento e você pode recarregar minutos a qualquer instante.")
