"""Triagem documental do piso mínimo; não substitui enquadramento regulatório."""
from datetime import date
from math import isfinite


def avaliar_piso(operacao, coeficientes):
    """Só calcula operações completas de lotação com coeficiente compatível.

    Recebe um cadastro já validado externamente. Não deduz tabela, categoria,
    distância ou configuração a partir do valor pago ou do peso do item.
    Valor de transporte deve excluir pedágio para comparação homogênea.
    """
    required = ["data_transporte", "distancia_km", "eixos", "categoria_carga",
                "tabela", "modalidade", "valor_transporte_sem_pedagio",
                "retorno_vazio_obrigatorio", "enquadramento_validado"]
    missing = [k for k in required if operacao.get(k) is None or operacao.get(k) == ""]
    if missing:
        return {"status": "nao_avaliavel", "motivo": "Dados ausentes: " + ", ".join(missing)}
    if operacao["modalidade"] != "lotacao" or operacao["enquadramento_validado"] is not True:
        return {"status": "nao_avaliavel", "motivo": "Enquadramento não validado para este cálculo de lotação"}
    if operacao["retorno_vazio_obrigatorio"]:
        return {"status": "nao_avaliavel", "motivo": "Retorno obrigatório exige cálculo específico"}
    try:
        day = date.fromisoformat(str(operacao["data_transporte"])[:10])
        distance = float(operacao["distancia_km"])
        paid = float(operacao["valor_transporte_sem_pedagio"])
        if not isfinite(distance) or not isfinite(paid) or distance <= 0 or paid < 0:
            raise ValueError("Valores inválidos")
        matches = [c for c in coeficientes
                   if date.fromisoformat(c["vigencia_inicio"]) <= day <= date.fromisoformat(c["vigencia_fim"])
                   and int(c["eixos"]) == int(operacao["eixos"])
                   and c["categoria_carga"] == operacao["categoria_carga"]
                   and c["tabela"] == operacao["tabela"]]
        if len(matches) != 1:
            return {"status": "nao_avaliavel", "motivo": "Coeficiente ausente ou vigências ambíguas"}
        c = matches[0]
        if not c.get("url_fonte") or not c.get("ato_normativo"):
            return {"status": "nao_avaliavel", "motivo": "Coeficiente sem proveniência oficial registrada"}
        cc, ccd = float(c["coeficiente_carga_descarga"]), float(c["coeficiente_deslocamento"])
        if not all(isfinite(v) and v >= 0 for v in [cc, ccd]):
            raise ValueError("Coeficientes inválidos")
        floor = round(distance * ccd + cc, 2)
        return {"status": "abaixo_da_referencia" if paid < floor else "igual_ou_acima_da_referencia",
                "piso_referencia_rs": floor, "diferenca_rs": round(paid - floor, 2),
                "ato_normativo": c["ato_normativo"], "url_fonte": c["url_fonte"],
                "observacao": "Triagem condicionada ao enquadramento e dados declarados; pedágio separado."}
    except (ValueError, TypeError, KeyError, OverflowError):
        return {"status": "nao_avaliavel", "motivo": "Dados ou coeficientes inválidos"}
