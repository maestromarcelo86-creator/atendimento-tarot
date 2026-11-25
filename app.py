import streamlit as st
import time
import mercadopago
import stripe
from supabase import create_client
from streamlit_autorefresh import st_autorefresh

st.set_page_config(page_title="Consulta de Tarot & Vidência", page_icon="🔮", layout="centered")

PRECO_MINUTO = 3.99

# Conexão com Supabase
@st.cache_resource
def init_supabase():
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

supabase = init_supabase()

# Busca estado atual da sala no banco de dados
def get_sessao():
    res = supabase.table("sessao_tarot").select("*").eq("id", 1).execute()
    return res.data[0]

sessao = get_sessao()
agora = int(time.time())
segundos_restantes = sessao["segundos_restantes"]

# Atualiza o cronômetro ao vivo no banco de dados a cada 5 segundos
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

# --- BARRA LATERAL: ÁREA DO TARÓLOGO ---
eh_tarologo = False
with st.sidebar:
    st.header("🔮 Área do Tarólogo")
    senha = st.text_input("Senha de Administrador", type="password")
    if senha == st.secrets.get("SENHA_TAROLOGO", "1760"):
        eh_tarologo = True
        st.success("Painel Liberado")
        online = st.toggle("Estou Online", value=sessao["tarologo_online"])
        if online != sessao["tarologo_online"]:
            supabase.table("sessao_tarot").update({"tarologo_online": online}).eq("id", 1).execute()
            st.rerun()

        st.subheader("Controle de Tempo")
        mins_manual = st.number_input("Minutos para adicionar:", min_value=1, value=10)
        if st.button("✅ Liberar / Somar Minutos"):
            novo_saldo = segundos_restantes + (mins_manual * 60)
            supabase.table("sessao_tarot").update({
                "segundos_restantes": novo_saldo,
                "ultimo_tick": int(time.time())
            }).eq("id", 1).execute()
            st.rerun()

        if st.button("⏹️ Encerrar e Zerar Tempo"):
            supabase.table("sessao_tarot").update({"segundos_restantes": 0}).eq("id", 1).execute()
            st.rerun()

        if st.button("🗑️ Limpar Histórico do Chat"):
            supabase.table("mensagens_tarot").delete().neq("id", 0).execute()
            st.rerun()

# --- TELA PRINCIPAL ---
st.title("🔮 Consulta Espiritual & Tarot")
status_txt = "🟢 Tarólogo Online" if sessao["tarologo_online"] else "🔴 Tarólogo Offline no momento"
st.write(f"**{status_txt}** • Atendimento por Chat ou Vídeo • **R$ {PRECO_MINUTO:.2f} / min**")

# 1. SALA DE ATENDIMENTO AO VIVO (CHAT + VÍDEO + CRONÔMETRO)
if segundos_restantes > 0:
    mins = segundos_restantes // 60
    segs = segundos_restantes % 60
    st.info(f"⏳ **Tempo Restante na Sala:** {mins:02d}:{segs:02d}")

    aba_chat, aba_video = st.tabs(["💬 Chat ao Vivo", "📹 Vídeo ao Vivo"])

    with aba_chat:
        msgs = supabase.table("mensagens_tarot").select("*").order("id").execute().data
        for m in msgs:
            with st.chat_message(m["autor"]):
                st.write(m["texto"])

        novo_texto = st.chat_input("Digite sua mensagem...")
        if novo_texto:
            autor = "assistant" if eh_tarologo else "user"
            supabase.table("mensagens_tarot").insert({"autor": autor, "texto": novo_texto}).execute()
            st.rerun()

    with aba_video:
        st.write("Clique em **Entrar na reunião** abaixo para abrir câmera e áudio:")
        st.components.v1.iframe("https://jit.si", height=500)
else:
    st.warning("Saldo de minutos zerado. Escolha abaixo seu tempo e forma de pagamento para iniciar.")

# 2. COMPRA DE MINUTOS (PIX, CRÉDITO, DÉBITO E DEPÓSITO)
st.divider()
st.subheader("⏱️ Comprar Minutos de Consulta")

col1, col2 = st.columns(2)
with col1:
    minutos_escolhidos = st.selectbox("Escolha os minutos:", [5, 10, 15, 20, 30, 60], index=1)
with col2:
    valor_total = round(minutos_escolhidos * PRECO_MINUTO, 2)
    st.metric("Valor Total", f"R$ {valor_total:.2f}")

forma_pagto = st.radio(
    "Forma de pagamento:",
    [
        "💠 Mercado Pago (Pix, Crédito ou Débito)",
        "💳 Stripe (Cartão de Crédito / Internacional)",
        "🏦 Depósito / Transferência Bancária"
    ]
)

if forma_pagto == "💠 Mercado Pago (Pix, Crédito ou Débito)":
    if st.button("Gerar Pagamento (Pix / Crédito / Débito)"):
        sdk = mercadopago.SDK(st.secrets["MP_ACCESS_TOKEN"])
        preferencia = {
            "items": [{
                "title": f"Consulta Tarot - {minutos_escolhidos} minutos",
                "quantity": 1,
                "currency_id": "BRL",
                "unit_price": float(valor_total)
            }],
            "payment_methods": {
                "installments": 6
            }
        }
        res = sdk.preference().create(preferencia)
        if "init_point" in res["response"]:
            st.session_state.mp_pref_id = res["response"]["id"]
            st.link_button("👉 Pagar agora (Pix, Crédito ou Débito)", res["response"]["init_point"])
            st.caption("Após concluir o pagamento na aba do Mercado Pago, clique no botão de confirmar abaixo.")
        else:
            st.error("Erro ao gerar link do Mercado Pago. Verifique seu MP_ACCESS_TOKEN.")

    if "mp_pref_id" in st.session_state:
        if st.button("✅ Já paguei no Mercado Pago (Liberar Minutos)"):
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
                st.success("Pagamento confirmado! Minutos liberados.")
                st.rerun()
            else:
                st.warning("Pagamento ainda não identificado. Aguarde alguns segundos e clique novamente.")

elif forma_pagto == "💳 Stripe (Cartão de Crédito / Internacional)":
    if st.button("Gerar Link de Cartão (Stripe)"):
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
            success_url="https://streamlit.io",
            cancel_url="https://streamlit.io",
        )
        st.session_state.stripe_session_id = sessao_stripe.id
        st.link_button("👉 Pagar com Cartão no Stripe", sessao_stripe.url)

    if "stripe_session_id" in st.session_state:
        if st.button("✅ Já paguei no Stripe (Liberar Minutos)"):
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
                st.warning("Pagamento ainda não confirmado no Stripe.")

elif forma_pagto == "🏦 Depósito / Transferência Bancária":
    st.info("""
    **Dados da Conta Bancária para Depósito / TED:**
    * **Banco:** Coloque seu banco aqui
    * **Agência:** 0001 • **Conta:** 123456-7
    * **Favorecido:** Seu Nome Completo
    """)
    comprovante = st.file_uploader("Anexe o comprovante do depósito:", type=["png", "jpg", "jpeg", "pdf"])
    if comprovante:
        st.success("Comprovante recebido! O tarólogo irá conferir e liberar seus minutos na hora.")
