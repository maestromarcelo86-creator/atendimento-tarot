import streamlit as st
import time
from datetime import date, timedelta
import mercadopago
import stripe
from supabase import create_client
from streamlit_autorefresh import st_autorefresh

st.set_page_config(
    page_title="Marcelo Astrologo | Tarot, Vidência e Astrologia",
    page_icon="🔮",
    layout="centered",
    initial_sidebar_state="collapsed"
)

PRECO_MINUTO = 3.99

if "pagamento_confirmado" not in st.session_state:
    st.session_state.pagamento_confirmado = False
if "minutos_pagos" not in st.session_state:
    st.session_state.minutos_pagos = 0

st.markdown("""
<style>
    .stApp { background: linear-gradient(180deg, #120924 0%, #1d1035 50%, #0e071c 100%); color: #f3e8ff; }
    h1, h2, h3, h4 { color: #f5d061 !important; font-family: 'Georgia', serif; }
    .hero-box { background: rgba(255, 255, 255, 0.05); border: 1px solid rgba(245, 208, 97, 0.4); border-radius: 18px; padding: 26px 20px; text-align: center; margin-bottom: 20px; }
    .subtitle-gold { color: #f5d061; font-size: 14px; letter-spacing: 1.5px; text-transform: uppercase; font-weight: bold; margin-bottom: 8px; }
    .status-badge-on { background-color: rgba(16, 185, 129, 0.2); color: #6ee7b7; border: 1px solid #10b981; padding: 5px 15px; border-radius: 20px; font-weight: bold; font-size: 13px; display: inline-block; margin-bottom: 12px; }
    .status-badge-off { background-color: rgba(239, 68, 68, 0.2); color: #fca5a5; border: 1px solid #ef4444; padding: 5px 15px; border-radius: 20px; font-weight: bold; font-size: 13px; display: inline-block; margin-bottom: 12px; }
    .timer-box { background: linear-gradient(90deg, #3b1d6e 0%, #5829a7 100%); border: 2px solid #f5d061; border-radius: 12px; padding: 15px; text-align: center; font-size: 24px; font-weight: bold; color: #ffffff; margin-bottom: 16px; }
    .spec-card { background: rgba(255, 255, 255, 0.04); border: 1px solid rgba(245, 208, 97, 0.25); border-radius: 12px; padding: 14px; text-align: center; min-height: 140px; margin-bottom: 10px; }
    .pkg-card { background: rgba(245, 208, 97, 0.07); border: 1px solid rgba(245, 208, 97, 0.35); border-radius: 12px; padding: 14px; text-align: center; margin-bottom: 10px; }
    .stButton>button { background: linear-gradient(90deg, #d4af37 0%, #f5d061 100%); color: #120924 !important; font-weight: bold; border: none; border-radius: 10px; padding: 12px 20px; width: 100%; }
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
        st.error(f"Erro de conexão: {e}")
        st.stop()

sessao = get_sessao()
agora = int(time.time())
segundos_restantes = sessao.get("segundos_restantes", 0)

if segundos_restantes > 0:
    st_autorefresh(interval=5000, key="cronometro_ao_vivo")
    decorrido = agora - sessao.get("ultimo_tick", agora)
    if decorrido >= 5:
        novo_tempo = max(0, segundos_restantes - decorrido)
        supabase.table("sessao_tarot").update({"segundos_restantes": novo_tempo, "ultimo_tick": agora}).eq("id", 1).execute()
        segundos_restantes = novo_tempo

eh_tarologo = False
with st.sidebar:
    st.header("🔮 Painel - Marcelo Astrologo")
    senha = st.text_input("Senha de Administrador", type="password")
    if senha == st.secrets.get("SENHA_TAROLOGO", "1760"):
        eh_tarologo = True
        st.success("Painel Liberado")
        online = st.toggle("Status Online no Site", value=sessao.get("tarologo_online", True))
        if online != sessao.get("tarologo_online", True):
            supabase.table("sessao_tarot").update({"tarologo_online": online}).eq("id", 1).execute()
            st.rerun()
        mins_manual = st.number_input("Adicionar minutos:", min_value=1, value=10)
        if st.button("✅ Liberar Sala Agora (Minutos)"):
            novo_saldo = segundos_restantes + (mins_manual * 60)
            supabase.table("sessao_tarot").update({"segundos_restantes": novo_saldo, "ultimo_tick": int(time.time())}).eq("id", 1).execute()
            st.rerun()
        if st.button("📅 Liberar Agendamento (Depósito)"):
            st.session_state.pagamento_confirmado = True
            st.session_state.minutos_pagos = mins_manual
            st.rerun()
        if st.button("⏹️ Encerrar Consulta"):
            supabase.table("sessao_tarot").update({"segundos_restantes": 0}).eq("id", 1).execute()
            st.rerun()
        if st.button("🗑️ Limpar Histórico do Chat"):
            supabase.table("mensagens_tarot").delete().neq("id", 0).execute()
            st.rerun()

        st.divider()
        st.subheader("📅 Agenda de Clientes Pagos")
        agenda = supabase.table("agendamentos_tarot").select("*").order("data_consulta").order("horario").execute().data
        if not agenda:
            st.caption("Nenhum horário agendado no momento.")
        for ag in agenda:
            st.info(f"**{ag.get('data_consulta')} às {ag.get('horario')}**\n\n👤 {ag.get('nome_cliente')} • 📱 {ag.get('whatsapp')}\n\n🔮 {ag.get('servico')}")
            if st.button(f"❌ Cancelar #{ag.get('id')}", key=f"del_{ag.get('id')}"):
                supabase.table("agendamentos_tarot").delete().eq("id", ag.get("id")).execute()
                st.rerun()
badge = '<span class="status-badge-on">🟢 DISPONÍVEL PARA CONSULTA AO VIVO</span>' if sessao.get("tarologo_online", True) else '<span class="status-badge-off">🔴 EM ATENDIMENTO / OFFLINE</span>'

st.markdown(f"""
<div class="hero-box">
    {badge}
    <div class="subtitle-gold">Tarólogo • Espírita Vidente • Astrólogo</div>
    <h1>🔮 Marcelo Astrologo</h1>
    <p style="font-size: 16px; color: #e2d4f0;">
        Consultoria espiritual completa, tiragem de Tarot, vidência espírita, Astrologia e leitura de Mapa Astral.<br>
        Atendimento sigiloso por <b>Chat</b> ou <b>Vídeo</b> • <b>R$ {PRECO_MINUTO:.2f} / minuto</b>
    </p>
</div>
""", unsafe_allow_html=True)

if segundos_restantes > 0:
    mins = segundos_restantes // 60
    segs = segundos_restantes % 60
    st.markdown(f'<div class="timer-box">⏳ Tempo Restante na Consulta: {mins:02d}:{segs:02d}</div>', unsafe_allow_html=True)
    aba_chat, aba_video = st.tabs(("💬 Chat ao Vivo", "📹 Vídeo ao Vivo"))
    with aba_chat:
        msgs = supabase.table("mensagens_tarot").select("*").order("id").execute().data
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
        st.components.v1.iframe("https://jit.si", height=520)
    st.divider()

st.subheader("✨ Áreas de Atendimento & Consultoria")
e1, e2, e3 = st.columns(3)
with e1:
    st.markdown('<div class="spec-card"><h4>🃏 Tarot & Vidência</h4><p style="font-size:14px;">Respostas sobre amor, finanças, decisões e revelações espirituais.</p></div>', unsafe_allow_html=True)
with e2:
    st.markdown('<div class="spec-card"><h4>🌌 Astrologia & Mapa Astral</h4><p style="font-size:14px;">Mapa natal, trânsitos astrológicos, sinastria amorosa e ciclos.</p></div>', unsafe_allow_html=True)
with e3:
    st.markdown('<div class="spec-card"><h4>🕊️ Consultoria Espiritual</h4><p style="font-size:14px;">Orientação espírita, limpeza energética e direcionamento.</p></div>', unsafe_allow_html=True)

st.divider()
st.subheader("⏱️ 1º Passo: Adquirir Minutos de Consulta")
c1, c2, c3 = st.columns(3)
with c1:
    st.markdown(f'<div class="pkg-card"><h4>🌙 Objetiva</h4><h3>10 Minutos</h3><p>R$ {10*PRECO_MINUTO:.2f}</p></div>', unsafe_allow_html=True)
with c2:
    st.markdown(f'<div class="pkg-card"><h4>⭐ Mais Escolhido</h4><h3>20 Minutos</h3><p>R$ {20*PRECO_MINUTO:.2f}</p></div>', unsafe_allow_html=True)
with c3:
    st.markdown(f'<div class="pkg-card"><h4>👑 Completa</h4><h3>30 Minutos</h3><p>R$ {30*PRECO_MINUTO:.2f}</p></div>', unsafe_allow_html=True)

col_sel, col_val = st.columns(2)
with col_sel:
    minutos_escolhidos = st.selectbox("Duração desejada (minutos):", (5, 10, 15, 20, 30, 45, 60), index=1)
with col_val:
    valor_total = round(minutos_escolhidos * PRECO_MINUTO, 2)
    st.metric("Valor Total", f"R$ {valor_total:.2f}")

forma_pagto = st.radio("Forma de pagamento:", ("💠 Mercado Pago (Pix, Crédito ou Débito)", "💳 Stripe (Cartão de Crédito)", "🏦 Depósito / Transferência (Banco Safra)"))

if forma_pagto == "💠 Mercado Pago (Pix, Crédito ou Débito)":
    if st.button("Gerar Link de Pagamento (Pix / Cartão)"):
        sdk = mercadopago.SDK(st.secrets.get("MP_ACCESS_TOKEN"))
        item_mp = {"title": f"Consulta Marcelo Astrologo - {minutos_escolhidos} min", "quantity": 1, "currency_id": "BRL", "unit_price": float(valor_total)}
        res = sdk.preference().create({"items": list((item_mp,)), "payment_methods": {"installments": 6}})
        resp_mp = res.get("response", {})
        if "init_point" in resp_mp:
            st.session_state.mp_pref_id = resp_mp.get("id")
            st.link_button("👉 Abrir Pagamento Seguro (Mercado Pago)", resp_mp.get("init_point"))
    if "mp_pref_id" in st.session_state:
        if st.button("✅ Já realizei o pagamento (Liberar Sala e Agenda)"):
            sdk = mercadopago.SDK(st.secrets.get("MP_ACCESS_TOKEN"))
            busca = sdk.payment().search({"sort": "date_created", "criteria": "desc", "limit": 5})
            aprovado = False
            for p in busca.get("response", {}).get("results", ()):
                if p.get("status") == "approved" and float(p.get("transaction_amount", 0)) == float(valor_total):
                    if st.session_state.get("ultimo_pgto_liberado") != p.get("id"):
                        st.session_state.ultimo_pgto_liberado = p.get("id")
                        aprovado = True
                        break
            if aprovado:
                st.session_state.pagamento_confirmado = True
                st.session_state.minutos_pagos = minutos_escolhidos
                novo_saldo = segundos_restantes + (minutos_escolhidos * 60)
                supabase.table("sessao_tarot").update({"segundos_restantes": novo_saldo, "ultimo_tick": int(time.time())}).eq("id", 1).execute()
                st.rerun()
            else:
                st.warning("Aguardando confirmação do pagamento. Aguarde 5 segundos e clique novamente.")

elif forma_pagto == "💳 Stripe (Cartão de Crédito)":
    if st.button("Gerar Link no Cartão (Stripe)"):
        stripe.api_key = st.secrets.get("STRIPE_SECRET_KEY")
        item_stripe = {"price_data": {"currency": "brl", "product_data": {"name": f"Consulta Marcelo Astrologo ({minutos_escolhidos} min)"}, "unit_amount": int(valor_total * 100)}, "quantity": 1}
        sessao_stripe = stripe.checkout.Session.create(payment_method_types=list(("card",)), line_items=list((item_stripe,)), mode="payment", success_url="https://streamlit.io", cancel_url="https://streamlit.io")
        st.session_state.stripe_session_id = sessao_stripe.id
        st.link_button("👉 Pagar com Cartão no Stripe", sessao_stripe.url)
    if "stripe_session_id" in st.session_state:
        if st.button("✅ Já paguei no Stripe (Liberar Sala e Agenda)"):
            stripe.api_key = st.secrets.get("STRIPE_SECRET_KEY")
            check = stripe.checkout.Session.retrieve(st.session_state.stripe_session_id)
            if check.payment_status == "paid":
                st.session_state.pagamento_confirmado = True
                st.session_state.minutos_pagos = minutos_escolhidos
                novo_saldo = segundos_restantes + (minutos_escolhidos * 60)
                supabase.table("sessao_tarot").update({"segundos_restantes": novo_saldo, "ultimo_tick": int(time.time())}).eq("id", 1).execute()
                del st.session_state.stripe_session_id
                st.rerun()
            else:
                st.warning("Pagamento ainda não confirmado pelo cartão.")

elif forma_pagto == "🏦 Depósito / Transferência (Banco Safra)":
    st.info("**Dados Bancários (TED/DOC):**\n* **Banco:** Banco Safra (Código 422)\n* **Agência:** 0115\n* **Conta Corrente:** 342955-9\n* **Favorecido:** Marcelo Astrologo")
    comprovante = st.file_uploader("Anexe o comprovante (foto ou PDF):", type=list(("png", "jpg", "jpeg", "pdf")))
    if comprovante:
        st.success("Comprovante enviado! Marcelo Astrologo irá validar para liberar sua sala e agenda.")

st.divider()
st.subheader("📅 2º Passo: Agendar Dia e Horário Certo")

if st.session_state.pagamento_confirmado or eh_tarologo:
    st.success(f"🔓 Pagamento confirmado ({st.session_state.minutos_pagos} min)! Escolha abaixo o dia e horário da sua consulta:")
    col_d1, col_d2 = st.columns(2)
    with col_d1:
        data_escolhida = st.date_input("Escolha o dia:", min_value=date.today(), max_value=date.today() + timedelta(days=60), format="DD/MM/YYYY")
        data_str = data_escolhida.strftime("%d/%m/%Y")

    todos_horarios = ("09:00", "10:00", "11:00", "13:00", "14:00", "15:00", "16:00", "17:00", "18:00", "19:00", "20:00", "21:00")
    ocupados_res = supabase.table("agendamentos_tarot").select("horario").eq("data_consulta", data_str).execute().data
    horarios_ocupados = tuple(item.get("horario") for item in ocupados_res)
    horarios_livres = tuple(h for h in todos_horarios if h not in horarios_ocupados)

    with col_d2:
        if horarios_livres:
            horario_escolhido = st.selectbox("Horários disponíveis neste dia:", horarios_livres)
        else:
            horario_escolhido = None
            st.warning("Todos os horários desta data já estão preenchidos. Escolha outro dia.")

    col_n1, col_n2 = st.columns(2)
    with col_n1:
        nome_ag = st.text_input("Seu Nome Completo:", placeholder="Ex: Maria Silva")
    with col_n2:
        whats_ag = st.text_input("Seu WhatsApp (com DDD):", placeholder="Ex: (11) 99999-9999")

    servico_ag = st.selectbox("Assunto da Consulta:", ("🃏 Tarot & Vidência", "🌌 Astrologia & Mapa Astral", "🕊️ Consultoria Espiritual"))

    if st.button("📅 Confirmar Horário Pago"):
        if not horarios_livres:
            st.error("Selecione uma data com horários disponíveis.")
        elif not nome_ag.strip() or not whats_ag.strip():
            st.warning("Preencha seu nome e WhatsApp para confirmar o horário.")
        else:
            supabase.table("agendamentos_tarot").insert({
                "data_consulta": data_str,
                "horario": horario_escolhido,
                "nome_cliente": nome_ag.strip(),
                "whatsapp": whats_ag.strip(),
                "servico": f"{servico_ag} ({st.session_state.minutos_pagos} min pagos)"
            }).execute()
            st.session_state.pagamento_confirmado = False
            st.success(f"✅ Horário reservado e confirmado para **{data_str} às {horario_escolhido}** com Marcelo Astrologo!")
else:
st.subheader("📅 2º Passo: Agendar Dia e Horário Certo")

if st.session_state.pagamento_confirmado or eh_tarologo:
    st.success(f"🔓 Pagamento confirmado ({st.session_state.minutos_pagos} min)! Escolha abaixo o dia e horário da sua consulta:")
    col_d1, col_d2 = st.columns(2)
    with col_d1:
        data_escolhida = st.date_input("Escolha o dia:", min_value=date.today(), max_value=date.today() + timedelta(days=60), format="DD/MM/YYYY")
        data_str = data_escolhida.strftime("%d/%m/%Y")

    todos_horarios = ("09:00", "10:00", "11:00", "13:00", "14:00", "15:00", "16:00", "17:00", "18:00", "19:00", "20:00", "21:00")
    ocupados_res = supabase.table("agendamentos_tarot").select("horario").eq("data_consulta", data_str).execute().data
    horarios_ocupados = tuple(item.get("horario") for item in ocupados_res)
    horarios_livres = tuple(h for h in todos_horarios if h not in horarios_ocupados)

    with col_d2:
        if horarios_livres:
            horario_escolhido = st.selectbox("Horários disponíveis neste dia:", horarios_livres)
        else:
            horario_escolhido = None
            st.warning("Todos os horários desta data já estão preenchidos. Escolha outro dia.")

    col_n1, col_n2 = st.columns(2)
    with col_n1:
        nome_ag = st.text_input("Seu Nome Completo:", placeholder="Ex: Maria Silva")
    with col_n2:
        whats_ag = st.text_input("Seu WhatsApp (com DDD):", placeholder="Ex: (11) 99999-9999")

    servico_ag = st.selectbox("Assunto da Consulta:", ("🃏 Tarot & Vidência", "🌌 Astrologia & Mapa Astral", "🕊️ Consultoria Espiritual"))

    if st.button("📅 Confirmar Horário Pago"):
        if not horarios_livres:
            st.error("Selecione uma data com horários disponíveis.")
        elif not nome_ag.strip() or not whats_ag.strip():
            st.warning("Preencha seu nome e WhatsApp para confirmar o horário.")
        else:
            supabase.table("agendamentos_tarot").insert({
                "data_consulta": data_str,
                "horario": horario_escolhido,
                "nome_cliente": nome_ag.strip(),
                "whatsapp": whats_ag.strip(),
                "servico": f"{servico_ag} ({st.session_state.minutos_pagos} min pagos)"
            }).execute()
            st.session_state.pagamento_confirmado = False
            st.success(f"✅ Horário reservado e confirmado para **{data_str} às {horario_escolhido}** com Marcelo Astrologo!")
else:
    st.warning("🔒 **Agenda Bloqueada:** Para escolher e reservar um dia e horário exclusivo, realize primeiro o pagamento dos seus minutos no **1º Passo** acima.")

st.divider()
col_info1, col_info2 = st.columns(2)
with col_info1:
    st.markdown("**🔒 Sigilo Absoluto**\n\nTodas as consultas com Marcelo Astrologo são 100% confidenciais.")
with col_info2:
    st.markdown("**⏳ Tempo Transparente**\n\nO cronômetro inicia apenas após a confirmação do pagamento.")
