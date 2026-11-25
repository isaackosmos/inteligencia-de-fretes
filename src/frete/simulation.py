"""Cenários transparentes; valores financeiros sempre em reais e pesos em toneladas."""
from math import isfinite


def _positive(value, name, zero=True):
    value = float(value)
    if not isfinite(value) or value < 0 or (not zero and value == 0):
        raise ValueError(f"{name} deve ser um número {'não negativo' if zero else 'positivo'}.")
    return value


def volume_scenario(segments, volume_t, mix=None, adjustment_pct=0):
    """Repondera tarifas históricas por um mix escolhido, sem inferência causal."""
    volume_t = _positive(volume_t, "Volume")
    adjustment_pct = float(adjustment_pct)
    if not isfinite(adjustment_pct) or adjustment_pct < -100:
        raise ValueError("Reajuste deve ser finito e maior ou igual a -100%.")
    segments = list(segments)
    destinations = [str(s['destino']) for s in segments]
    if len(destinations) != len(set(destinations)):
        raise ValueError('Segmentos contêm destinos duplicados.')
    tariffs = {str(s['destino']): _positive(s['tarifa_rs_t'], 'Tarifa') for s in segments}
    if not tariffs:
        raise ValueError('Não há segmentos com volume positivo.')
    weights = {str(s['destino']): s['peso_t'] for s in segments} if mix is None else mix
    weights = {str(k): _positive(v, 'Participação') for k, v in weights.items()}
    if set(weights) - set(tariffs):
        raise ValueError('O mix contém destino sem histórico filtrado.')
    total = sum(weights.values())
    if total <= 0 or not isfinite(total):
        raise ValueError('O mix deve conter ao menos uma participação positiva.')
    tariff = sum(tariffs[k] * v / total for k, v in weights.items()) * (1 + adjustment_pct / 100)
    if not isfinite(tariff) or not isfinite(tariff * volume_t):
        raise ValueError('Resultado do cenário excede a faixa numérica finita.')
    return {'volume_t': volume_t, 'tarifa_rs_t': tariff, 'custo_rs': tariff * volume_t,
            'metodo': 'Tarifas históricas ponderadas pelo mix; não é previsão do modelo.'}


def component_scenario(distance_km, diesel_rs_l, consumption_km_l, toll_rs,
                       capacity_t, utilization_pct, other_rs_km=0, fixed_rs=0,
                       margin_pct=0):
    """Custo de uma viagem; distância e pedágio devem representar o mesmo percurso."""
    distance = _positive(distance_km, 'Distância')
    diesel = _positive(diesel_rs_l, 'Diesel')
    consumption = _positive(consumption_km_l, 'Consumo', zero=False)
    toll = _positive(toll_rs, 'Pedágio')
    capacity = _positive(capacity_t, 'Capacidade', zero=False)
    utilization = _positive(utilization_pct, 'Ocupação', zero=False)
    margin = _positive(margin_pct, 'Acréscimo')
    if utilization > 100:
        raise ValueError('Ocupação deve ser de até 100%.')
    fuel = distance / consumption * diesel
    other = distance * _positive(other_rs_km, 'Outros custos por km') + _positive(fixed_rs, 'Custo fixo')
    base = fuel + toll + other
    cost = base * (1 + margin / 100)
    weight = capacity * utilization / 100
    if weight <= 0 or not all(isfinite(v) for v in (fuel, other, base, cost, weight, cost / weight)):
        raise ValueError('Resultado da viagem excede a faixa numérica finita ou peso calculado é zero.')
    return {'diesel_rs': fuel, 'pedagio_rs': toll, 'outros_rs': other,
            'acrescimo_rs': cost - base, 'custo_rs': cost, 'peso_t': weight,
            'tarifa_rs_t': cost / weight,
            'metodo': 'Estimativa paramétrica por viagem; não verifica piso ANTT.'}
