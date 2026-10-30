"""Failure-path tests for analysis/demand_analysis.py (no live database needed)."""

import os
import subprocess
import sys

import pandas as pd
import pytest
from sqlalchemy import create_engine

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(PROJECT_ROOT, 'analysis', 'demand_analysis.py')
sys.path.insert(0, os.path.join(PROJECT_ROOT, 'analysis'))


@pytest.fixture(scope='module')
def demand_analysis():
    # The module reads GROCERY_DB_PASSWORD and calls load_dotenv() at import;
    # stub both so the test never reads a real .env
    with pytest.MonkeyPatch.context() as mp:
        mp.setenv('GROCERY_DB_PASSWORD', 'unused')
        mp.setattr('dotenv.load_dotenv', lambda *args, **kwargs: False)
        import demand_analysis
        yield demand_analysis


def one_estimate():
    return pd.DataFrame([{
        'upc': 100001, 'category': 'Dairy', 'true_elasticity': -0.8,
        'estimated_elasticity': -0.79, 'error': 0.01, 'error_pct': 1.25,
        'std_err': 0.01, 'ci_lower': -0.81, 'ci_upper': -0.77,
        'truth_in_ci': True, 'r_squared': 0.6, 'p_value': 0.0,
        'observations': 730, 'price_cv': 0.08,
    }])


def test_unreachable_database_exits_nonzero():
    # Run as a subprocess so we check the real exit status Airflow's
    # BashOperator sees. Port 1 refuses connections immediately.
    env = {
        **os.environ,
        'GROCERY_DB_HOST': '127.0.0.1',
        'GROCERY_DB_PORT': '1',
        'GROCERY_DB_NAME': 'none',
        'GROCERY_DB_USER': 'nobody',
        'GROCERY_DB_PASSWORD': 'unused',
    }
    result = subprocess.run([sys.executable, SCRIPT], env=env, cwd=PROJECT_ROOT,
                            capture_output=True, text=True, timeout=60)
    assert result.returncode != 0
    assert 'Database connection failed' in result.stderr


def test_failed_estimates_write_exits_nonzero(demand_analysis):
    # SQLite has no CREATE SCHEMA, so the write fails with a SQLAlchemyError
    engine = create_engine('sqlite://')
    with pytest.raises(SystemExit, match='Failed to write raw.elasticity_estimates'):
        demand_analysis.persist_estimates(engine, one_estimate())


def test_no_estimates_exits_nonzero(demand_analysis):
    engine = create_engine('sqlite://')
    with pytest.raises(SystemExit, match='No elasticity estimates'):
        demand_analysis.persist_estimates(engine, one_estimate().iloc[0:0])
