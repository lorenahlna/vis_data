import streamlit as st
import pandas as pd
import requests

# Configuração da página do Streamlit
st.set_page_config(page_title="Painel Social MDS", layout="wide")

st.title("📊 Explorador de Dados Sociais")
st.markdown("Consulta em tempo real à API do **Portal Brasileiro de Dados Abertos (dados.gov.br)**.")

# Função cacheadada para não sobrecarregar a API com chamadas repetidas
@st.cache_data
def buscar_bases_governo(termo):
    """Busca bases de dados na API CKAN do dados.gov.br"""
    # Endpoint de busca de pacotes do CKAN
    url = f"https://dados.gov.br/api/3/action/package_search?q={termo}"
    
    try:
        resposta = requests.get(url, timeout=10)
        if resposta.status_code == 200:
            return resposta.json()['result']['results']
    except Exception as e:
        st.error(f"Erro ao conectar com a API: {e}")
    return []

# Interface do Usuário
termo_pesquisa = st.text_input("Qual programa você quer investigar?", "Bolsa Familia")

if st.button("Buscar na API"):
    with st.spinner("Consultando servidores do Governo Federal..."):
        datasets = buscar_bases_governo(termo_pesquisa)
        
        if datasets:
            st.success(f"Encontramos {len(datasets)} bases de dados relacionadas!")
            
            # Loop para desenhar os resultados na tela
            for data in datasets:
                with st.expander(f"📁 {data['title']}"):
                    st.write(data.get('notes', 'Sem descrição detalhada.'))
                    
                    st.markdown("**Arquivos disponíveis nesta base:**")
                    recursos = data.get('resources', [])
                    
                    for rec in recursos:
                        # Extrai o link e o formato do arquivo (CSV, JSON, PDF, etc)
                        formato = rec.get('format', 'N/A').upper()
                        link = rec.get('url', '#')
                        st.markdown(f"- 📄 `{formato}`: [Clique para acessar/baixar]({link})")
                        
                        # Dica: Se for CSV, você pode pegar o 'link' e jogar direto num pd.read_csv(link) 
                        # para plotar gráficos no próprio Streamlit nas próximas etapas!
        else:
            st.warning("Nenhuma base encontrada. Tente termos como 'CadÚnico', 'BPC' ou 'CRAS'.")
