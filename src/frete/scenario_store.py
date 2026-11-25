"""Cenários em memória, JSON versionado e comparações de premissas explícitas.

Nenhuma função grava em disco. Resultados recebidos por importação são ignorados.
"""
from copy import deepcopy
from datetime import datetime, timezone
import json
from math import isclose, isfinite
from uuid import UUID, uuid4

from frete.simulation import component_scenario, volume_scenario

SCHEMA_VERSION = 1
MAX_SCENARIOS = 30
MAX_JSON_BYTES = 1_000_000
MAX_SEGMENTS = 200
TRIP_KEYS = {'distance_km', 'diesel_rs_l', 'consumption_km_l', 'toll_rs', 'capacity_t',
             'utilization_pct', 'other_rs_km', 'fixed_rs', 'margin_pct'}
TRIP_REQUIRED = {'distance_km', 'diesel_rs_l', 'consumption_km_l', 'toll_rs', 'capacity_t', 'utilization_pct'}


def _json_value(value, depth=0):
    if depth > 10:
        raise ValueError('JSON excede profundidade máxima de 10 níveis.')
    if value is None or type(value) is bool:
        return
    if type(value) in (int, float):
        try:
            valid = isfinite(value)
        except OverflowError:
            valid = False
        if not valid:
            raise ValueError('JSON contém número não finito ou excessivo.')
    elif isinstance(value, str):
        if len(value) > 4096:
            raise ValueError('Texto excede limite de 4096 caracteres.')
    elif isinstance(value, list):
        if len(value) > 1000:
            raise ValueError('Lista excede limite de 1000 elementos.')
        for child in value:
            _json_value(child, depth + 1)
    elif isinstance(value, dict):
        if len(value) > 500 or any(not isinstance(k, str) or len(k) > 200 for k in value):
            raise ValueError('Objeto JSON tem chaves inválidas ou em excesso.')
        for child in value.values():
            _json_value(child, depth + 1)
    else:
        raise ValueError('Valor não pertence aos tipos JSON aceitos.')


def _copy_json(value):
    _json_value(value)
    try:
        encoded = json.dumps(value, ensure_ascii=False, allow_nan=False)
    except (TypeError, ValueError, OverflowError, RecursionError) as error:
        raise ValueError('Conteúdo JSON inválido.') from error
    if len(encoded.encode('utf-8')) > MAX_JSON_BYTES:
        raise ValueError(f'Conteúdo excede {MAX_JSON_BYTES} bytes.')
    return json.loads(encoded)


def _number(value, name):
    if type(value) not in (int, float):
        raise ValueError(f'{name} deve ser número JSON, não texto ou booleano.')
    try:
        result = float(value)
    except (OverflowError, ValueError) as error:
        raise ValueError(f'{name} excede faixa numérica.') from error
    if not isfinite(result):
        raise ValueError(f'{name} deve ser finito.')
    return result


def _parameters(kind, parameters):
    if not isinstance(parameters, dict):
        raise ValueError('parameters deve ser objeto JSON.')
    p = _copy_json(parameters)
    if kind == 'viagem':
        if set(p) - TRIP_KEYS or not TRIP_REQUIRED.issubset(p):
            raise ValueError('Parâmetros da viagem ausentes ou desconhecidos.')
        return {k: _number(v, k) for k, v in p.items()}
    if kind != 'mix':
        raise ValueError('Tipo deve ser mix ou viagem.')
    if set(p) - {'segments', 'volume_t', 'mix', 'adjustment_pct'} or not {'segments', 'volume_t'}.issubset(p):
        raise ValueError('Parâmetros do mix ausentes ou desconhecidos.')
    segments = p['segments']
    if not isinstance(segments, list) or not 1 <= len(segments) <= MAX_SEGMENTS:
        raise ValueError(f'Mix deve ter de 1 a {MAX_SEGMENTS} segmentos.')
    for segment in segments:
        if not isinstance(segment, dict) or set(segment) != {'destino', 'peso_t', 'tarifa_rs_t'}:
            raise ValueError('Cada segmento deve conter destino, peso_t e tarifa_rs_t.')
        if not isinstance(segment['destino'], str) or not segment['destino'].strip() or len(segment['destino']) > 200:
            raise ValueError('Destino deve ser texto não vazio de até 200 caracteres.')
        for key in ('peso_t', 'tarifa_rs_t'):
            segment[key] = _number(segment[key], key)
            if segment[key] < 0:
                raise ValueError(f'{key} não pode ser negativo.')
    p['volume_t'] = _number(p['volume_t'], 'volume_t')
    p['adjustment_pct'] = _number(p.get('adjustment_pct', 0), 'adjustment_pct')
    if p.get('mix') is not None:
        if not isinstance(p['mix'], dict):
            raise ValueError('mix deve ser objeto de participações por destino.')
        p['mix'] = {k: _number(v, 'Participação') for k, v in p['mix'].items()}
    return p


def create_scenario(kind, name, parameters, scope, origin, scenario_id=None, created_at=None):
    """Cria snapshot independente; identidade existente serve para reimportação."""
    if not isinstance(name, str) or not name.strip() or len(name.strip()) > 120:
        raise ValueError('Nome deve conter de 1 a 120 caracteres.')
    if not isinstance(scope, dict) or not isinstance(origin, (dict, str)) or not origin:
        raise ValueError('scope deve ser objeto e origin deve identificar a origem.')
    scope, origin = _copy_json(scope), _copy_json(origin)
    if len(json.dumps([scope, origin], ensure_ascii=False).encode('utf-8')) > 32_000:
        raise ValueError('Escopo e origem excedem 32000 bytes.')
    if scenario_id is None:
        scenario_id = str(uuid4())
    if not isinstance(scenario_id, str):
        raise ValueError('ID de cenário inválido.')
    try:
        if str(UUID(scenario_id)) != scenario_id:
            raise ValueError('ID deve ser UUID canônico.')
    except (ValueError, AttributeError) as error:
        raise ValueError('ID deve ser UUID canônico.') from error
    if created_at is None:
        created_at = datetime.now(timezone.utc).isoformat()
    try:
        if not isinstance(created_at, str):
            raise ValueError('Data inválida.')
        timestamp = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
        if timestamp.utcoffset() is None or timestamp.utcoffset().total_seconds() != 0:
            raise ValueError('Data deve declarar UTC.')
    except (TypeError, ValueError) as error:
        raise ValueError('created_at_utc deve ser data ISO8601 em UTC.') from error
    p = _parameters(kind, parameters)
    try:
        result = volume_scenario(**p) if kind == 'mix' else component_scenario(**p)
    except (TypeError, KeyError, OverflowError, ZeroDivisionError) as error:
        raise ValueError('Falha numérica ou parâmetros inválidos no cenário.') from error
    return _copy_json({'id': scenario_id, 'name': name.strip(), 'created_at_utc': created_at,
                       'kind': kind, 'unit': 'R$/t', 'parameters': p, 'scope': scope,
                       'origin': origin, 'result': result})


def _recalculate(scenario):
    if not isinstance(scenario, dict):
        raise ValueError('Cenário deve ser objeto JSON.')
    allowed = {'id', 'name', 'created_at_utc', 'kind', 'unit', 'parameters', 'scope', 'origin', 'result'}
    if set(scenario) - allowed or not (allowed - {'result'}).issubset(scenario):
        raise ValueError('Campos do cenário ausentes ou desconhecidos.')
    if scenario['unit'] != 'R$/t':
        raise ValueError('Unidade não suportada; esperado R$/t.')
    return create_scenario(scenario['kind'], scenario['name'], scenario['parameters'], scenario['scope'],
                           scenario['origin'], scenario['id'], scenario['created_at_utc'])


class ScenarioStore:
    """Coleção para st.session_state ou outro estado de sessão; sem disco."""
    def __init__(self, initial=None):
        self._scenarios = {}
        if initial is not None:
            if not isinstance(initial, list):
                raise ValueError('initial deve ser lista de cenários.')
            self.import_json({'schema_version': SCHEMA_VERSION, 'scenarios': initial})

    def list(self):
        return deepcopy(list(self._scenarios.values()))

    def add(self, scenario):
        scenario = _recalculate(_copy_json(scenario))
        if len(self._scenarios) >= MAX_SCENARIOS:
            raise ValueError(f'Limite de {MAX_SCENARIOS} cenários por sessão.')
        if scenario['id'] in self._scenarios:
            raise ValueError('ID de cenário já existe na sessão.')
        self._scenarios[scenario['id']] = scenario
        return deepcopy(scenario)

    def create(self, *args, **kwargs):
        return self.add(create_scenario(*args, **kwargs))

    def remove(self, scenario_id):
        if not isinstance(scenario_id, str) or scenario_id not in self._scenarios:
            raise ValueError('Cenário não encontrado na sessão.')
        return deepcopy(self._scenarios.pop(scenario_id))

    def export_json(self):
        return json.dumps(_copy_json({'schema_version': SCHEMA_VERSION, 'scenarios': self.list()}), ensure_ascii=False, indent=2, allow_nan=False)

    def import_json(self, payload):
        """Valida o lote inteiro antes de incorporar qualquer cenário."""
        if isinstance(payload, (str, bytes)):
            try:
                if len(payload if isinstance(payload, bytes) else payload.encode('utf-8')) > MAX_JSON_BYTES:
                    raise ValueError('Arquivo JSON excede limite de tamanho.')
                payload = json.loads(payload, parse_constant=lambda value: (_ for _ in ()).throw(ValueError(f'Constante JSON inválida: {value}')))
            except (UnicodeDecodeError, json.JSONDecodeError, RecursionError) as error:
                raise ValueError('Arquivo JSON inválido.') from error
        payload = _copy_json(payload)
        if not isinstance(payload, dict) or set(payload) != {'schema_version', 'scenarios'}:
            raise ValueError('Documento deve conter schema_version e scenarios.')
        if type(payload['schema_version']) is not int or payload['schema_version'] != SCHEMA_VERSION:
            raise ValueError('Versão de cenários não suportada.')
        incoming = payload['scenarios']
        if not isinstance(incoming, list) or len(incoming) + len(self._scenarios) > MAX_SCENARIOS:
            raise ValueError(f'Limite de {MAX_SCENARIOS} cenários por sessão.')
        rebuilt = [_recalculate(s) for s in incoming]
        ids = [s['id'] for s in rebuilt]
        if len(ids) != len(set(ids)) or set(ids) & set(self._scenarios):
            raise ValueError('IDs duplicados na importação ou já existentes na sessão.')
        self._scenarios.update({s['id']: s for s in rebuilt})
        return deepcopy(rebuilt)

    def compare(self, base_id, alternative_id, normalize_volume_t=None):
        if base_id == alternative_id:
            raise ValueError('Selecione dois cenários distintos.')
        try:
            a, b = self._scenarios[base_id], self._scenarios[alternative_id]
        except (KeyError, TypeError) as error:
            raise ValueError('Cenário não encontrado na sessão.') from error
        if a['kind'] != b['kind'] or a['unit'] != b['unit']:
            raise ValueError('Comparação exige mesmo tipo e unidade.')
        if a['scope'] != b['scope'] or a['origin'] != b['origin']:
            raise ValueError('Comparação exige mesmo escopo de filtros e origem.')
        volume_key = 'volume_t' if a['kind'] == 'mix' else 'peso_t'
        va, vb = a['result'][volume_key], b['result'][volume_key]
        normalized = normalize_volume_t is not None
        if normalized:
            volume = _number(normalize_volume_t, 'Volume de normalização')
            if volume <= 0 or va <= 0 or vb <= 0:
                raise ValueError('Normalização exige volumes positivos.')
        else:
            if not isclose(va, vb, rel_tol=1e-12, abs_tol=1e-9):
                raise ValueError('Volumes diferentes; informe normalização explícita.')
            volume = va
        warnings = []
        if normalized:
            warnings.append('Normalização linear mantém a tarifa de cada cenário; não recalcula capacidade, número inteiro de viagens ou efeitos de escala.')

        def components(scenario):
            result, p = scenario['result'], scenario['parameters']
            if scenario['kind'] == 'viagem':
                ratio = volume / result['peso_t']
                return {key: result[key] * ratio for key in ('diesel_rs', 'pedagio_rs', 'outros_rs', 'acrescimo_rs')}
            weights = p.get('mix')
            if weights is None:
                weights = {s['destino']: s['peso_t'] for s in p['segments']}
            total = sum(weights.values())
            tariffs = {s['destino']: s['tarifa_rs_t'] for s in p['segments']}
            return {key: tariffs[key] * (weight / total) * (1 + p['adjustment_pct'] / 100) * volume for key, weight in weights.items()}

        ca, cb = components(a), components(b)
        decomposition = [{'component': key, 'base_rs': ca.get(key, 0), 'alternative_rs': cb.get(key, 0),
                          'delta_rs': cb.get(key, 0) - ca.get(key, 0)} for key in sorted(set(ca) | set(cb))]
        def brief(scenario):
            return {'id': scenario['id'], 'name': scenario['name'], 'custo_rs': scenario['result']['tarifa_rs_t'] * volume,
                    'tarifa_rs_t': scenario['result']['tarifa_rs_t']}
        ba, bb = brief(a), brief(b)
        response = {'kind': a['kind'], 'unit': a['unit'], 'volume_t': volume, 'normalized': normalized,
                    'base': ba, 'alternative': bb, 'delta_custo_rs': bb['custo_rs'] - ba['custo_rs'],
                    'delta_tarifa_rs_t': bb['tarifa_rs_t'] - ba['tarifa_rs_t'], 'decomposition': decomposition,
                    'scope_base': a['scope'], 'scope_alternative': b['scope'], 'origin_base': a['origin'],
                    'origin_alternative': b['origin'], 'warnings': warnings,
                    'interpretation': 'Diferença paramétrica entre premissas; não demonstra economia realizada nem conformidade ANTT.'}
        return _copy_json(response)
