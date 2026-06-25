# VERSAO_FINAL_SOCIAL_PRODUCAO_V3
import streamlit as st
import pandas as pd
import requests
import time
import threading
from datetime import datetime

# --- CONFIGURAÇÃO DE DESIGN DA PÁGINA ---
st.set_page_config(
    page_title="Inteligência Territorial | Dados Sociais",
    page_icon="🏠",
    layout="wide"
)

st.markdown("""
    <style>
    .header-mds { background-color: #006633; padding: 20px; color: white; border-radius: 5px; text-align: center; margin-bottom: 20px; }
    .stButton>button { background-color: #006633; color: white; width: 100%; border: none; }
    .stButton>button:hover { background-color: #004d26; }
    .metric-card { background-color: #f0f2f6; padding: 15px; border-radius: 10px; border-left: 5px solid #006633; text-align: center; margin-bottom: 15px;}
    .footer-text { text-align: center; color: #666; font-size: 14px; margin-top: 50px; padding-top: 20px; border-top: 1px solid #ddd; }
    </style>
""", unsafe_allow_html=True)

# --- TRAVA DE CONCORRÊNCIA GLOBAL ---
@st.cache_resource
def obter_trava_global():
    return threading.Lock()

trava_global = obter_trava_global()

# --- CONSTANTES TERRITORIAIS ---
UFS = ["AC","AL","AP","AM","BA","CE","DF","ES","GO","MA","MT","MS","MG","PA","PB","PR","PE","PI","RJ","RN","RS","RO","RR","SC","SP","SE","TO"]
ESTADOS_IBGE = {"AC": "12", "AL": "27", "AP": "16", "AM": "13", "BA": "29", "CE": "23", "DF": "53", "ES": "32", "GO": "52", "MA": "21", "MT": "51", "MS": "50", "MG": "31", "PA": "15", "PB": "25", "PR": "41", "PE": "26", "PI": "22", "RJ": "33", "RN": "24", "RS": "43", "RO": "11", "RR": "14", "SC": "42", "SP": "35", "SE": "28", "TO": "17"}

MESES_NOMES = [
    "01 - Janeiro", "02 - Fevereiro", "03 - Março", "04 - Abril",
    "05 - Maio", "06 - Junho", "07 - Julho", "08 - Agosto",
    "09 - Setembro", "10 - Outubro", "11 - Novembro", "12 - Dezembro"
]

@st.cache_data
def buscar_municipios_por_uf(uf_sigla):
    url = f"https://servicodados.ibge.gov.br/api/v1/localidades/estados/{uf_sigla}/municipios"
    try:
        res = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10).json()
        return {m['nome']: {"id_ibge": str(m['id']), "nome": m['nome'], "uf": uf_sigla} for m in res}
    except:
        return {"Belo Horizonte": {"id_ibge": "3106200", "nome": "Belo Horizonte", "uf": "MG"}}

# --- MOTOR DE EXTRAÇÃO DE DADOS SOCIAIS (API REAL CORRIGIDA) ---
def extrair_dados_sociais(sistema, uf, municipio, ano, mes):
    local = municipio if municipio else uf
    
    # Busca a chave de API de forma segura
    try:
        api_token = st.secrets["CHAVE_API_CGU"]
    except KeyError:
        st.error("⚠️ Chave da API não configurada. Configure 'CHAVE_API_CGU' no Streamlit Secrets.")
        return pd.DataFrame()

    # Busca o código IBGE do município
    id_ibge = None
    if municipio:
        muns_estado = buscar_municipios_por_uf(uf)
        if municipio in muns_estado:
            id_ibge = muns_estado[municipio]['id_ibge']
            
    headers = {"chave-api-dados": api_token}
    
    # Formata Competência para a API (Ex: Janeiro de 2024 vira "202401")
    ano_mes_competencia = f"{ano}{mes:02d}" if mes else f"{ano}"

    data = []

    # ---------------------------------------------------------
    # DADOS REAIS: PORTAL DA TRANSPARÊNCIA (Bolsa Família, BPC, Gás)
    # ---------------------------------------------------------
    if sistema == "Programa Bolsa Família (PBF)" and id_ibge:
        # Rota atualizada para o "Novo Bolsa Família" com paginação obrigatória
        url = f"https://api.portaldatransparencia.gov.br/api-de-dados/novo-bolsa-familia-por-municipio?codigoIbge={id_ibge}&mesAno={ano_mes_competencia}&pagina=1"
        try:
            res = requests.get(url, headers=headers, timeout=15)
            if res.status_code == 200:
                res_json = res.json()
                if len(res_json) > 0:
                    dados_api = res_json[0]
                    qtd_familias = dados_api.get('quantidadeBeneficiarios', 0)
                    valor_pago = dados_api.get('valor', 0.0)
                    
                    data = [{
                        "TERRITÓRIO": local, "ANO": ano, "MÊS": mes,
                        "FAMÍLIAS_BENEFICIÁRIAS": qtd_familias,
                        "VALOR_TOTAL_REPASSADO": valor_pago,
                        "TICKET_MÉDIO_FAMÍLIA": valor_pago / qtd_familias if qtd_familias > 0 else 0,
                        "ACOMPANHAMENTO_SAÚDE_PERC": "Via Datasus",
                        "FREQUÊNCIA_ESCOLAR_PERC": "Via MEC" 
                    }]
                    return pd.DataFrame(data)
            else:
                st.warning(f"A API do Governo recusou a conexão ou não há dados. Código: {res.status_code}")
        except Exception as e:
            st.error(f"Erro na conexão com a API da Transparência: {e}")

    # BPC
    elif sistema == "Benefício de Prestação Continuada (BPC)" and id_ibge:
        url = f"https://api.portaldatransparencia.gov.br/api-de-dados/bpc-por-municipio?codigoIbge={id_ibge}&mesAno={ano_mes_competencia}&pagina=1"
        try:
            res = requests.get(url, headers=headers, timeout=15)
            if res.status_code == 200:
                res_json = res.json()
                if len(res_json) > 0:
                    dados_api = res_json[0]
                    qtd_beneficios = dados_api.get('quantidadeBeneficiarios', 0)
                    
                    data = [{
                        "TERRITÓRIO": local, "ANO": ano, "MÊS": mes,
                        "BPC_IDOSO_ATIVOS": int(qtd_beneficios * 0.4), # Divisão visual aproximada
                        "BPC_PCD_ATIVOS": int(qtd_beneficios * 0.6),   # Divisão visual aproximada
                        "NOVAS_CONCESSÕES_MÊS": "Via INSS",
                        "VALOR_TOTAL_PAGO": dados_api.get('valor', 0.0)
                    }]
                    return pd.DataFrame(data)
            else:
                st.warning(f"A API do Governo recusou a conexão ou não há dados. Código: {res.status_code}")
        except Exception as e:
            st.error(f"Erro na conexão com a API da Transparência: {e}")

    # Auxílio Gás
    elif sistema == "Programas Complementares (Gás / PAA)" and id_ibge:
        url = f"https://api.portaldatransparencia.gov.br/api-de-dados/auxilio-gas-por-municipio?codigoIbge={id_ibge}&mesAno={ano_mes_competencia}&pagina=1"
        try:
            res = requests.get(url, headers=headers, timeout=15)
            if res.status_code == 200:
                res_json = res.json()
                if len(res_json) > 0:
                    dados_api = res_json[0]
                    data = [{
                        "TERRITÓRIO": local, "ANO": ano, "MÊS": mes,
                        "AUXÍLIO_GÁS_FAMÍLIAS": dados_api.get('quantidadeBeneficiarios', 0),
                        "AUXÍLIO_GÁS_VALOR": dados_api.get('valor', 0.0),
                        "PAA_AGRICULTORES_FORNECEDORES": "Sem dados financeiros",
                        "PAA_VALOR_INVESTIDO": "Sem dados financeiros"
                    }]
                    return pd.DataFrame(data)
            else:
                st.warning(f"A API do Governo recusou a conexão ou não há dados. Código: {res.status_code}")
        except Exception as e:
            pass

    # ---------------------------------------------------------
    # DADOS ESTRUTURAIS/MOCKADOS (Bases que não estão na Transparência)
    # ---------------------------------------------------------
    time.sleep(0.5)
    if sistema == "Cadastro Único (CadÚnico)":
        data = [{
            "TERRITÓRIO": local, "ANO": ano, "MÊS": mes,
            "TOTAL_FAMÍLIAS_INSCRITAS": 45200,
            "TOTAL_PESSOAS_INSCRITAS": 128500,
            "EXTREMA_POBREZA": 18500,
            "POBREZA": 8200,
            "BAIXA_RENDA": 11000,
            "ACIMA_MEIO_SALÁRIO": 7500,
            "FAMÍLIAS_INDÍGENAS": 120,
            "FAMÍLIAS_QUILOMBOLAS": 340,
            "FAMÍLIAS_CIGANAS": 15
        }]
    elif sistema == "Estrutura da Assistência Social (Censo SUAS)":
        data = [{
            "TERRITÓRIO": local, "ANO": ano,
            "QTD_CRAS": 8,
            "QTD_CREAS": 2,
            "QTD_CENTRO_POP": 1,
            "ASSISTENTES_SOCIAIS": 45,
            "PSICÓLOGOS": 22,
            "CAPACIDADE_ATENDIMENTO_FAMÍLIAS": 40000
        }]
        
    return pd.DataFrame(data)

# --- INTERFACE PRINCIPAL ---
st.sidebar.title("🏠 Navegação MDS")
aba_ativa = st.sidebar.radio("Navegar para:", ["📋 Extração de Dados", "📚 Metodologia e Dicionário"])

if aba_ativa == "📋 Extração de Dados":
    st.markdown('<div class="header-mds"><h1>Inteligência Territorial | Dados Sociais</h1><p>Integração com bases do Ministério do Desenvolvimento e Assistência Social (MDS)</p></div>', unsafe_allow_html=True)
    
    nivel_terr = st.sidebar.radio("Nível Territorial:", ["Estado", "Município"])
    ufs_ordenadas = sorted(UFS)
    
    municipio_sel = None
    if nivel_terr == "Estado":
        uf_sel = st.sidebar.selectbox("Selecione o Estado:", ufs_ordenadas, index=ufs_ordenadas.index("MG"))
        nome_local = uf_sel
    elif nivel_terr == "Município":
        uf_sel = st.sidebar.selectbox("Filtrar Estado:", ufs_ordenadas, index=ufs_ordenadas.index("MG"))
        muns_estado = buscar_municipios_por_uf(uf_sel)
        mun_nome = st.sidebar.selectbox("Selecione o Município:", sorted(muns_estado.keys()))
        municipio_sel = mun_nome
        nome_local = f"{mun_nome} ({uf_sel})"

    sistema = st.sidebar.selectbox("Programa / Base de Dados:", [
        "Programa Bolsa Família (PBF)", 
        "Benefício de Prestação Continuada (BPC)", 
        "Programas Complementares (Gás / PAA)",
        "Cadastro Único (CadÚnico)", 
        "Estrutura da Assistência Social (Censo SUAS)"
    ])
    
    # Anos recentes costumam ter mais estabilidade na API da Transparência
    ano_sel = st.sidebar.selectbox("Ano de Referência:", list(range(2026, 2012, -1)))
    
    # Censo SUAS é anual, removemos o mês se for selecionado
    if sistema == "Estrutura da Assistência Social (Censo SUAS)":
        st.sidebar.info("O Censo SUAS possui consolidação anual. Filtro de mês desabilitado.")
        mes_sel = None
    else:
        # Default para o mês anterior ao atual para garantir que a base já foi fechada
        mes_padrao = datetime.now().month - 1 if datetime.now().month > 1 else 12
        nome_mes = st.sidebar.selectbox("Mês de Competência:", MESES_NOMES, index=mes_padrao - 1)
        mes_sel = int(nome_mes.split(" - ")[0])

    with st.sidebar.form("form_consulta_social"):
        submit_button = st.form_submit_button("🔍 Processar Indicadores")

    if submit_button:
        if nivel_terr == "Estado" and sistema in ["Programa Bolsa Família (PBF)", "Benefício de Prestação Continuada (BPC)", "Programas Complementares (Gás / PAA)"]:
            st.warning("⚠️ Para consultar bases reais financeiras, selecione a opção 'Município' na barra lateral.")
        else:
            with trava_global:
                with st.spinner(f"Acessando base agregada do {sistema} para {nome_local}..."):
                    df_resultado = extrair_dados_sociais(sistema, uf_sel, municipio_sel, ano_sel, mes_sel)
                    
                    if not df_resultado.empty:
                        # Formata o texto de competência dinamicamente (Ano/Mês ou só Ano)
                        if mes_sel is not None:
                            texto_competencia = f"{mes_sel:02d}/{ano_sel}"
                        else:
                            texto_competencia = f"{ano_sel} (Consolidado Anual)"

                        st.markdown(f'<div class="metric-card"><h2>{sistema}</h2><p>Território: {nome_local} | Competência: {texto_competencia}</p></div>', unsafe_allow_html=True)
                        
                        tab1, tab2 = st.tabs(["📈 Painel Analítico", "✅ Base de Dados (Tabela)"])
                        
                        with tab1:
                            # --- DASHBOARDS ESPECÍFICOS POR SISTEMA ---
                            if sistema == "Cadastro Único (CadÚnico)":
                                st.info("ℹ️ Dados estruturais exibidos são demonstrativos. A conexão será implementada via base agregada do MDS.")
                                c1, c2, c3 = st.columns(3)
                                c1.metric("👨‍👩‍👧‍👦 Total de Famílias", f"{df_resultado['TOTAL_FAMÍLIAS_INSCRITAS'].iloc[0]:,}".replace(',', '.'))
                                c2.metric("👤 Total de Pessoas", f"{df_resultado['TOTAL_PESSOAS_INSCRITAS'].iloc[0]:,}".replace(',', '.'))
                                c3.metric("🚨 Famílias em Extrema Pobreza", f"{df_resultado['EXTREMA_POBREZA'].iloc[0]:,}".replace(',', '.'))
                                
                                st.markdown("### Composição de Renda")
                                df_renda = pd.DataFrame({
                                    "Faixa": ["Extrema Pobreza", "Pobreza", "Baixa Renda", "Acima Meio Salário"],
                                    "Famílias": [
                                        df_resultado['EXTREMA_POBREZA'].iloc[0],
                                        df_resultado['POBREZA'].iloc[0],
                                        df_resultado['BAIXA_RENDA'].iloc[0],
                                        df_resultado['ACIMA_MEIO_SALÁRIO'].iloc[0]
                                    ]
                                }).set_index("Faixa")
                                st.bar_chart(df_renda, color="#006633")
                                
                            elif sistema == "Programa Bolsa Família (PBF)":
                                c1, c2, c3 = st.columns(3)
                                c1.metric("💳 Famílias Beneficiárias", f"{df_resultado['FAMÍLIAS_BENEFICIÁRIAS'].iloc[0]:,}".replace(',', '.'))
                                c2.metric("💰 Repasse Total Mês", f"R$ {df_resultado['VALOR_TOTAL_REPASSADO'].iloc[0]:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'))
                                c3.metric("💵 Ticket Médio / Família", f"R$ {df_resultado['TICKET_MÉDIO_FAMÍLIA'].iloc[0]:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'))
                                
                                st.write("---")
                                st.markdown("### Acompanhamento de Condicionalidades")
                                c_a, c_b = st.columns(2)
                                c_a.metric("🩺 Saúde (Vacinação/Peso)", f"{df_resultado['ACOMPANHAMENTO_SAÚDE_PERC'].iloc[0]}")
                                c_b.metric("📚 Educação (Frequência)", f"{df_resultado['FREQUÊNCIA_ESCOLAR_PERC'].iloc[0]}")

                            elif sistema == "Benefício de Prestação Continuada (BPC)":
                                c1, c2, c3 = st.columns(3)
                                total_bpc = df_resultado['BPC_IDOSO_ATIVOS'].iloc[0] + df_resultado['BPC_PCD_ATIVOS'].iloc[0]
                                c1.metric("📝 Estimativa Benefícios Ativos", f"{total_bpc:,}".replace(',', '.'))
                                c2.metric("✨ Novas Concessões (Mês)", f"{df_resultado['NOVAS_CONCESSÕES_MÊS'].iloc[0]}")
                                c3.metric("💸 Investimento Federal", f"R$ {df_resultado['VALOR_TOTAL_PAGO'].iloc[0]:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'))
                                
                                st.markdown("### Perfil do Benefício (Estimativa Visual)")
                                df_bpc = pd.DataFrame({
                                    "Tipo": ["BPC Idoso", "BPC PcD"],
                                    "Quantidade": [df_resultado['BPC_IDOSO_ATIVOS'].iloc[0], df_resultado['BPC_PCD_ATIVOS'].iloc[0]]
                                }).set_index("Tipo")
                                st.bar_chart(df_bpc, color="#006633")

                            elif sistema == "Estrutura da Assistência Social (Censo SUAS)":
                                st.info("ℹ️ Dados estruturais exibidos são demonstrativos. A conexão será implementada via base agregada do MDS.")
                                c1, c2, c3 = st.columns(3)
                                c1.metric("🏢 CRAS Abertos", df_resultado['QTD_CRAS'].iloc[0])
                                c2.metric("🏬 CREAS Abertos", df_resultado['QTD_CREAS'].iloc[0])
                                c3.metric("👥 Capacidade Instalada (Famílias)", f"{df_resultado['CAPACIDADE_ATENDIMENTO_FAMÍLIAS'].iloc[0]:,}".replace(',', '.'))
                                
                                st.markdown("### Recursos Humanos Base (SUAS)")
                                df_rh = pd.DataFrame({
                                    "Cargo": ["Assistentes Sociais", "Psicólogos"],
                                    "Profissionais": [df_resultado['ASSISTENTES_SOCIAIS'].iloc[0], df_resultado['PSICÓLOGOS'].iloc[0]]
                                }).set_index("Cargo")
                                st.bar_chart(df_rh, color="#006633")
                                
                            elif sistema == "Programas Complementares (Gás / PAA)":
                                st.markdown("### Auxílio Gás")
                                c1, c2 = st.columns(2)
                                c1.metric("🔥 Famílias Beneficiárias", f"{df_resultado['AUXÍLIO_GÁS_FAMÍLIAS'].iloc[0]:,}".replace(',', '.'))
                                c2.metric("💵 Valor Repassado", f"R$ {df_resultado['AUXÍLIO_GÁS_VALOR'].iloc[0]:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'))
                                
                                st.write("---")
                                st.markdown("### Programa de Aquisição de Alimentos (PAA)")
                                c3, c4 = st.columns(2)
                                c3.metric("🚜 Agricultores Familiares", df_resultado['PAA_AGRICULTORES_FORNECEDORES'].iloc[0])
                                c4.metric("💰 Recurso Investido", f"{df_resultado['PAA_VALOR_INVESTIDO'].iloc[0]}")

                        with tab2:
                            st.dataframe(df_resultado, width='stretch')
                            csv = df_resultado.to_csv(index=False, sep=';', decimal=',')
                            st.download_button(
                                label="📥 Baixar Dados (CSV)",
                                data=csv,
                                file_name=f"{sistema.split(' (')[0]}_{nome_local}.csv",
                                mime="text/csv"
                            )
                    else:
                        st.error("Nenhum dado financeiro encontrado para este município no período selecionado. Tente buscar um mês anterior.")

# --- ABA DE DICIONÁRIOS E CITAÇÕES ---
elif aba_ativa == "📚 Metodologia e Dicionário":
    st.title("📚 Metodologia de Agregação Social (SAGICAD/MDS)")
    st.markdown("---")
    
    with st.expander("📋 Cadastro Único (CadÚnico)"):
        st.markdown("""
        O Cadastro Único é o principal instrumento do Estado brasileiro para identificação e caracterização socioeconômica das famílias de baixa renda.
        * **Extrema Pobreza:** Famílias com renda per capita mensal de até R$ 218,00.
        * **Pobreza:** Famílias com renda per capita mensal entre R$ 218,01 e meio salário mínimo.
        * **Grupos Tradicionais:** Marcador declaratório de pertencimento étnico/social (indígenas, quilombolas, ribeirinhos).
        """)
        
    with st.expander("💳 Programa Bolsa Família (PBF)"):
        st.markdown("""
        Substituto e sucessor do Auxílio Brasil, focado em transferência direta de renda com condicionalidades. Integrado via **Portal da Transparência da CGU**.
        * **Ticket Médio:** Valor da folha de pagamento dividido pelo total de famílias beneficiárias no território.
        * **Condicionalidades:** Monitoramento bimestral obrigatório realizado pelas redes de saúde (vacina/peso) e educação (frequência escolar mínima).
        """)
        
    with st.expander("📝 Benefício de Prestação Continuada (BPC/LOAS)"):
        st.markdown("""
        Garantia de 1 salário mínimo mensal à pessoa com deficiência e ao idoso com 65 anos ou mais que comprovem não possuir meios de prover a própria manutenção. Integrado via **Portal da Transparência da CGU**.
        * **Espécie 87:** BPC Pessoa com Deficiência (PcD).
        * **Espécie 88:** BPC Idoso.
        """)

    st.markdown("---")
    st.markdown("💡 **Nota Técnica de Implementação:** *Esta interface reflete dados oficiais do Portal da Transparência do Governo Federal para transferência de renda. Os dados estruturais de SUAS e CadÚnico estão estruturados em mock até a integração com os repositórios Data Lake do MDS.*")
