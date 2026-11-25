import streamlit as st
import time
import mercadopago
import stripe
from streamlit_autorefresh import st_autorefresh

# Configuração da Página Única
st.set_page_config(page_title="Consulta de Tarot & Vidência", page_icon="🔮", layout="centered")

# Preço configurado
PRECO_MINUTO = 3.99

# Atualiza a tela a cada 5 segundos quando houver atendimento ativo para rodar o cronômetro
if "atendimento_ativo" not in st.session_state:
    st.session_state.atendimento_ativo = False
if "segundos_restantes" not in st.session_state:
    st.session_state.segundos_restantes = 0
if "mensagens" not in st.session_state:
    st.session_state.mensagens = []
if "ultimo_tick" not in st.session_state:
    st.session_state.ultimo_tick = time.time()

if st.session_state.atendimento_ativo and st.session_state.segundos_restantes > 0:
    st_autorefresh(interval=5000, key="cronometro_refresh")
    agora = time.time()
    decorrido = int(agora - st.session_state.ultimo_tick)
    st.session_state.segundos_restantes = max(0, st.session_state.segundos_restantes - decorrido)
    st.session_state.ultimo_tick = agora
    if st.session_state.segundos_restantes == 0:
        st.session_state.atendimento_ativo = False

# --- BARRA LATERAL: ACESSO DO TARÓLOGO ---
with st.sidebar:
    st.header("🔮 Área do Tarólogo")
    senha = st.text_input("Senha de Administrador", type="password")
    if senha == st.secrets.get("SENHA_TAROLOGO", "tarot123"):
        st.success("Painel Liberado")
        status_online = st.toggle("Estou Online para Atender", value=True)
        st.subheader("Liberação Manual (Depósito)")
        mins_manual = st.number_input("Minutos para liberar:", min_value=1, value=10)
        if st.button("✅ Liberar Tempo ao Cliente"):
            st.session_state.segundos_restantes += mins_manual * 60
            st.session_state.atendimento_ativo = True
            st.session_state.ultimo_tick = time.time()
            st.rerun()
        if st.button("⏹️ Encerrar Sessão"):
            st.session_state.segundos_restantes = 0
            st.session_state.atendimento_ativo = False
            st.rerun()

# --- TELA PRINCIPAL (CLIENTE + ATENDIMENTO) ---
st.title("🔮 Consulta Espiritual & Tarot")
st.write(f"Atendimento ao vivo por **Chat ou Vídeo** • Valor: **R$ {PRECO_MINUTO:.2f} / minuto**")

# 1. CRONÔMETRO E SALA ATIVA
if st.session_state.segundos_restantes > 0:
    mins = st.session_state.segundos_restantes // 60
    segs = st.session_state.segundos_restantes % 60
    st.info(f"⏳ **Tempo Restante:** {mins:02d}:{segs:02d}")

    aba_chat, aba_video = st.tabs(["💬 Atendimento por Chat", "📹 Atendimento por Vídeo"])

    with aba_chat:
        for msg in st.session_state.mensagens:
            with st.chat_message(msg["autor"]):
                st.write(msg["texto"])

        novo_texto = st.chat_input("Digite sua mensagem ou pergunta...")
        if novo_texto:
            remetente = "assistant" if senha == st.secrets.get("SENHA_TAROLOGO", "tarot123") else "user"
            st.session_state.mensagens.append({"autor": remetente, "texto": novo_texto})
            st.rerun()

    with aba_video:
        st.write("Clique em **Entrar na reunião** abaixo para iniciar o vídeo com câmera e áudio:")
        sala_id = "ConsultaTarotEspiritual2026"
        st.components.v1.iframe(f"https://jit.si{sala_id}", height=500)

else:
    st.warning("Seu saldo de minutos está zerado. Escolha seu tempo abaixo para iniciar.")

# 2. ÁREA DE COMPRA / RECARGA DE MINUTOS (SEMPRE VISÍVEL PARA RECARREGAR)
st.divider()
st.subheader("⏱️ Comprar Minutos de Consulta")

col1, col2 = st.columns(2)
with col1:
    minutos_escolhidos = st.selectbox("Escolha o tempo:", [5, 10, 15, 20, 30, 60], index=1)
with col2:
    valor_total = round(minutos_escolhidos * PRECO_MINUTO, 2)
    st.metric("Valor Total", f"R$ {valor_total:.2f}")

forma_pagto = st.radio(
    "Escolha a forma de pagamento:",
    ["💠 Pix (Mercado Pago)", "💳 Cartão de Crédito (Stripe)", "🏦 Depósito / Transferência Bancária"],
    horizontal=True
)

if forma_pagto == "💠 Pix (Mercado Pago)":
    if st.button("Gerar QR Code Pix"):
        try:
            sdk = mercadopago.SDK(st.secrets["MP_ACCESS_TOKEN"])
            pagamento_data = {
                "transaction_amount": float(valor_total),
                "description": f"Consulta Tarot - {minutos_escolhidos} minutos",
                "payment_method_id": "pix",
                "payer": {"email": "cliente@consulta.com"}
            }
            res = sdk.payment().create(pagamento_data)
            qr_code = res["response"]["point_of_interaction"]["transaction_data"]["qr_code"]
            st.success("Copie o código Pix abaixo e pague no app do seu banco:")
            st.code(qr_code, language="text")
            st.session_state.ultimo_id_mp = res["response"]["id"]
        except Exception as e:
            st.error("Configure sua chave MP_ACCESS_TOKEN nos segredos do Streamlit para ativar o Pix real.")

    if "ultimo_id_mp" in st.session_state:
        if st.button("✅ Já paguei o Pix (Verificar agora)"):
            sdk = mercadopago.SDK(st.secrets["MP_ACCESS_TOKEN"])
            status = sdk.payment().get(st.session_state.ultimo_id_mp)["response"]["status"]
            if status == "approved":
                st.session_state.segundos_restantes += minutos_escolhidos * 60
                st.session_state.atendimento_ativo = True
                st.session_state.ultimo_tick = time.time()
                st.rerun()
            else:
                st.warning("Pagamento ainda não confirmado. Aguarde alguns segundos e clique novamente.")

elif forma_pagto == "💳 Cartão de Crédito (Stripe)":
    if st.button("Pagar com Cartão (Stripe)"):
        try:
            stripe.api_key = st.secrets["STRIPE_SECRET_KEY"]
            sessao = stripe.checkout.Session.create(
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
            st.link_button("👉 Clique aqui para finalizar no Cartão", sessao.url)
        except Exception as e:
            st.error("Configure sua chave STRIPE_SECRET_KEY nos segredos do Streamlit para ativar o cartão.")

elif forma_pagto == "🏦 Depósito / Transferência Bancária":
    st.info("""
    **Dados para Depósito / TED:**
    * **Banco:** Seu Banco (ex: Nubank / Itaú / Caixa)
    * **Agência:** 0001 • **Conta:** 123456-7
    * **Favorecido:** Seu Nome Completo
    """)
    comprovante = st.file_uploader("Envie a foto ou PDF do comprovante:", type=["png", "jpg", "jpeg", "pdf"])
    if comprovante:
        st.success("Comprovante enviado! Aguarde o tarólogo validar e liberar seus minutos na tela.")
