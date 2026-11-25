from frete.compliance import avaliar_piso


def inputs():
    return ({"data_transporte": "2025-02-01", "distancia_km": 100, "eixos": 6,
             "categoria_carga": "teste", "tabela": "A", "modalidade": "lotacao",
             "valor_transporte_sem_pedagio": 350, "retorno_vazio_obrigatorio": False,
             "enquadramento_validado": True},
            [{"vigencia_inicio": "2025-01-01", "vigencia_fim": "2025-12-31", "eixos": 6,
              "categoria_carga": "teste", "tabela": "A", "coeficiente_deslocamento": 3,
              "coeficiente_carga_descarga": 100, "ato_normativo": "exemplo sintético",
              "url_fonte": "https://example.org/teste"}])


def test_nao_conclui_sem_informacoes():
    assert avaliar_piso({}, [])["status"] == "nao_avaliavel"


def test_calculo_sintetico_e_vigencia():
    op, co = inputs()
    assert avaliar_piso(op, co)["piso_referencia_rs"] == 400
    assert avaliar_piso(op, co)["status"] == "abaixo_da_referencia"
    op["data_transporte"] = "2026-01-01"
    assert avaliar_piso(op, co)["status"] == "nao_avaliavel"


def test_ambiguidade_e_retorno():
    op, co = inputs()
    assert avaliar_piso(op, co + co)["status"] == "nao_avaliavel"
    op["retorno_vazio_obrigatorio"] = True
    assert avaliar_piso(op, co)["status"] == "nao_avaliavel"
