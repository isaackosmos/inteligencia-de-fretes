"""Cotações demonstrativas baseadas no histórico e consultáveis por código."""
from contextlib import closing
from datetime import datetime, timezone
from math import isfinite
from pathlib import Path
import sqlite3
from uuid import uuid4

from frete.simulation import volume_scenario

STATUSES = ('Disponível', 'Em transporte', 'Concluído', 'Cancelado')


def estimate_quote(history, destination, cargo, weight_t):
    if not isfinite(weight_t) or weight_t <= 0:
        raise ValueError('Informe um peso positivo e finito.')
    rows = history[
        history['destino_frete'].eq(destination) & history['tipo_carga'].eq(cargo)
        & history['peso_liquido_t'].gt(0) & history['Valor líquido'].gt(0)
    ]
    if rows.empty:
        raise ValueError('Sem histórico para essa combinação no recorte.')
    volume = float(rows['peso_liquido_t'].sum())
    tariff = float(rows['Valor líquido'].sum()) / volume
    estimate = volume_scenario([
        {'destino': destination, 'peso_t': volume, 'tarifa_rs_t': tariff}
    ], weight_t)
    return {
        'destination': destination, 'cargo': cargo, 'weight_t': weight_t,
        'tariff': estimate['tarifa_rs_t'], 'cost': estimate['custo_rs'],
        'sample': len(rows),
    }


class QuoteStore:
    def __init__(self, path):
        self.path = Path(path)

    def _connect(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.path)
        try:
            connection.execute("""
                CREATE TABLE IF NOT EXISTS quotes (
                    code TEXT PRIMARY KEY, destination TEXT NOT NULL, cargo TEXT NOT NULL,
                    weight_t REAL NOT NULL, tariff REAL NOT NULL, cost REAL NOT NULL,
                    sample INTEGER NOT NULL, status TEXT NOT NULL, created_at TEXT NOT NULL
                )
            """)
        except sqlite3.Error:
            connection.close()
            raise
        connection.row_factory = sqlite3.Row
        return connection

    def create(self, estimate):
        code = 'FRT-' + uuid4().hex.upper()
        created_at = datetime.now(timezone.utc).isoformat()
        with closing(self._connect()) as connection, connection:
            connection.execute('INSERT INTO quotes VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)', (
                code, estimate['destination'], estimate['cargo'], estimate['weight_t'],
                estimate['tariff'], estimate['cost'], estimate['sample'], STATUSES[0], created_at,
            ))
        return code

    def get(self, code):
        if not self.path.is_file():
            return None
        with closing(self._connect()) as connection:
            row = connection.execute('SELECT * FROM quotes WHERE code = ?', (code.strip().upper(),)).fetchone()
        return dict(row) if row else None

    def set_status(self, code, status):
        if status not in STATUSES:
            raise ValueError('Status de frete desconhecido.')
        if not self.path.is_file():
            return False
        with closing(self._connect()) as connection, connection:
            updated = connection.execute('UPDATE quotes SET status = ? WHERE code = ?', (status, code))
            return updated.rowcount == 1
