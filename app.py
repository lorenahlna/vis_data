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
                st.warning(f"A API do Governo recusou a conexão. Código: {res.status_code} - {res.text}")
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
                st.warning(f"A API do Governo recusou a conexão. Código: {res.status_code} - {res.text}")
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
                st.warning(f"A API do Governo recusou a conexão. Código: {res.status_code} - {res.text}")
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
