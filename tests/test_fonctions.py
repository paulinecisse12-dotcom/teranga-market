"""
Tests unitaires des fonctions cles du projet (metriques, elasticite, monitoring).
Lances automatiquement par le CI (GitHub Actions) a chaque push.
Auto-suffisants : ils ne dependent ni de l'entrepot DuckDB ni des libs lourdes
(Prophet, MLflow) -> le CI reste rapide.
"""
import numpy as np


# --- Fonctions testees (memes formules que dans les notebooks / scripts) -----
def mae(y, yhat):
    return float(np.mean(np.abs(y - yhat)))

def rmse(y, yhat):
    return float(np.sqrt(np.mean((y - yhat) ** 2)))

def mape(y, yhat):
    m = y != 0
    return float(np.mean(np.abs((y[m] - yhat[m]) / y[m])) * 100)

def prix_optimal(cout, E):
    """Prix qui maximise la marge (elasticite constante), valide si E < -1."""
    return cout * E / (E + 1)

def psi(reference, recent, n_bins=10):
    bornes = np.quantile(reference, np.linspace(0, 1, n_bins + 1))
    bornes[0], bornes[-1] = -np.inf, np.inf
    rp = np.clip(np.histogram(reference, bins=bornes)[0] / len(reference), 1e-4, None)
    cp = np.clip(np.histogram(recent, bins=bornes)[0] / len(recent), 1e-4, None)
    return float(np.sum((cp - rp) * np.log(cp / rp)))


# --- Tests metriques de prevision --------------------------------------------
def test_mae_parfait_est_zero():
    y = np.array([1.0, 2.0, 3.0])
    assert mae(y, y) == 0.0

def test_mae_valeur():
    assert mae(np.array([2.0, 2.0]), np.array([1.0, 3.0])) == 1.0

def test_rmse_penalise_grosses_erreurs():
    # une grosse erreur pese plus lourd en RMSE qu'en MAE
    y = np.array([0.0, 0.0]); yhat = np.array([0.0, 10.0])
    assert rmse(y, yhat) > mae(y, yhat)

def test_mape_pourcentage():
    y = np.array([100.0, 100.0]); yhat = np.array([110.0, 90.0])
    assert round(mape(y, yhat), 1) == 10.0


# --- Test pricing : formule du prix optimal ----------------------------------
def test_prix_optimal_demande_elastique():
    # E = -2.5 -> markup = E/(E+1) = 1.6667 -> prix = 166.7 pour un cout de 100
    assert round(prix_optimal(100.0, -2.5), 1) == 166.7


# --- Tests monitoring : PSI --------------------------------------------------
def test_psi_distributions_identiques_est_nul():
    x = np.random.RandomState(0).normal(size=1000)
    assert psi(x, x) < 1e-6

def test_psi_detecte_une_derive():
    r = np.random.RandomState(0)
    ref = r.normal(0, 1, 2000)
    recent = r.normal(3, 1, 2000)          # distribution nettement decalee
    assert psi(ref, recent) > 0.25          # -> derive importante
