import streamlit as st

st.set_page_config(
    page_title="Fisco Chiaro Consulting - Fatturazione elettronica",
    layout="wide",
    page_icon="📄",
)

PRIMARY_BLUE = "#1f77b4"

# HEADER
col_logo, col_menu, col_user = st.columns([2, 5, 1])
with col_logo:
    st.markdown(
        f"<h1 style='color:{PRIMARY_BLUE};margin-bottom:0'>FISCO CHIARO CONSULTING</h1>",
        unsafe_allow_html=True,
    )
with col_menu:
    st.markdown("#### Dashboard | Clienti | Documenti")
with col_user:
    st.markdown("Operatore")

st.markdown("---")

st.subheader("📊 Dashboard")

st.write(
    """
Benvenuta nell'app di fatturazione **Fisco Chiaro Consulting**.

Da qui puoi:
- vedere e gestire le fatture emesse,
- creare una nuova fattura,
- gestire la rubrica clienti/fornitori (dalla pagina Documenti).
"""
)

col1, col2 = st.columns(2)
with col1:
    if st.button("📄 Vai ai documenti / fatture emesse"):
        st.switch_page("pages/02_Documenti.py")

with col2:
    if st.button("🧾 Crea nuova fattura"):
        st.switch_page("pages/03_Fattura.py")

st.markdown("---")
st.caption(
    "Fisco Chiaro Consulting – Emesse gestite dall'app, PDF generati automaticamente."
)
