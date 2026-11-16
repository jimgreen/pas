from types import SimpleNamespace

from pas.kernels import normalize_ca, normalize_lf, normalize_se


def test_normalize_se_keeps_statistics_and_state():
    value = SimpleNamespace(statistics=SimpleNamespace(converged=True, observable=True, iterations=3, objective=2.0, max_correction=0.1, residual_inf=0.01, rank=4, state_count=4, measurement_count=6, deficiency=0, prefiltered_measurement_count=1, pseudo_measurement_count=2, bad_data_count=0, normal_measurement_count=3), normal_measurements=[])
    result = normalize_se(value, SimpleNamespace(x=[1.0, 2.0]))
    assert result["converged"] is True
    assert result["state"] == [1.0, 2.0]
    assert result["statistics"]["measurement_count"] == 6


def test_normalize_lf_and_ca_return_serializable_summaries():
    lf = normalize_lf(SimpleNamespace(converged=True, iterations=2, normF=1e-8, failure_reason="", lf_result=None))
    ca = normalize_ca([SimpleNamespace(risk_source="BASE", risk_dist="Bus", risk_type="Voltage", risk_value=0.9, risk_info="low")], [])[0]
    assert lf["converged"] is True
    assert ca["n0_risk_count"] == 1
    assert ca["risks"][0]["risk_type"] == "Voltage"
