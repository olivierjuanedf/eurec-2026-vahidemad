# Review Critique du Projet — ElectricSystemPlanning

> Rédigée le 2026-04-03. Destinée à l'équipe enseignante et aux développeurs du projet.

## Diagnostic Général

Le projet est **techniquement solide** dans ses intentions : bonnes abstractions, typage Python cohérent, infrastructure Codespaces fonctionnelle, structure pédagogique progressive (3 séances). Mais il souffre de **plusieurs problèmes qui fragilisent l'expérience étudiante et la maintenabilité à long terme**, et le `PLAN.md` existant n'en adresse qu'une fraction — parfois avec de mauvaises priorités.

---

## Critique du PLAN.md Existant

### Ce qui est juste

- **1.3** (guidage infaisabilité) : priorité correcte, impact direct étudiant — **garder**
- **1.1** (README quickstart) : évident, bien identifié
- **3.1** (tests) : bien vu, mais **classé trop bas** en priorité

### Ce qui est contestable ou manquant

| Point PLAN.md | Critique |
|---|---|
| **2.1 Refactorer `dataset.py`** | Effort élevé, risque de casse élevé, gain pédagogique quasi nul pour les étudiants. À garder pour les enseignants, mais pas prioritaire. |
| **2.2 Migrer toy model vers JSON** | Potentiellement **contre-productif** : le fichier Python est plus lisible pour un débutant qu'un JSON avec des séries temporelles qui ne peuvent pas y tenir (déjà noté dans le PLAN.md lui-même). Effort moyen pour valeur pédagogique discutable. |
| **3.2 TODO → GitHub Issues** | Effort faible mais impact quasi nul sur les étudiants. Dernière priorité réelle. |
| **Non mentionné** | `requirements.txt` sans pins de version : bombe à retardement pour la reproductibilité |
| **Non mentionné** | Incohérence nommage `wind_onshore` vs `wind_on_shore` (M0 TODO) : bug latent actif |
| **Non mentionné** | `devcontainer.json` utilise `universal:2` : image de 10+ Go, build lent, mauvaise expérience |
| **Non mentionné** | Aucune CI (GitHub Actions) : impossible de savoir si le code est cassé sans le faire tourner |
| **Non mentionné** | PyPSA 0.35.1 vs 1.0 (M1 TODO) : dette technique majeure |

---

## Review Complète — Problèmes par Catégorie

### 🔴 Priorité 1 — Bloquants ou Risques Élevés

#### P1-A : `requirements.txt` — Versions non épinglées

`requirements.txt` n'épingle que `linopy==0.5.5` et `pypsa==0.35.1`. `numpy`, `pandas`, `matplotlib`, `cartopy` sont libres. Une montée de version non souhaitée peut casser silencieusement le code entre deux sessions de cours.

- **Effort** : 1h
- **Action** : Générer un fichier complet depuis le devcontainer actuel, puis nettoyer les dépendances indirectes non pertinentes.
- **Commande** :
  ```bash
  pip freeze | grep -E "numpy|pandas|matplotlib|cartopy|scipy|xarray" >> requirements.txt
  ```

---

#### P1-B : Incohérence de nommage des types de production (TODO M0)

`wind_onshore` vs `wind_on_shore` coexistent entre les clés CSV, les constantes Python et les fichiers JSON. Ce genre d'incohérence provoque des bugs silencieux : des données sont ignorées sans message d'erreur explicite.

- **Effort** : 2-4h
- **Action** :
  1. Cartographier toutes les variantes :
     ```bash
     grep -r "wind_on" . --include="*.py" --include="*.json" --include="*.csv" -l
     ```
  2. Choisir une convention unique en s'alignant sur le vocabulaire PyPSA (`wind_onshore`)
  3. Corriger de manière systématique avec sed ou un script dédié
  4. Vérifier que les clés dans les fichiers CSV ERAA correspondent bien

(OB, 4/4/2026; commit 7d6fab08) Hors du 4. qui resterait à vérifier/parfaire pour que ce point soit unifié sur "toute 
la ligne" (données inclues)
---

#### P1-C : Aucun message utile en cas d'infaisabilité

`my_toy_ex_italy.py` (bloc `else` ligne ~344) affiche un message générique. Un étudiant qui obtient `infeasible` est complètement bloqué — c'est le cas de blocage le plus fréquent signalé (TODO M7).

- **Effort** : 2-3h
- **Action** : Remplacer le bloc `else` générique par un diagnostic structuré. Exemple pour `my_toy_ex_italy.py` :
  ```python
  else:
      print("\n❌ OPTIMISATION INFEASIBLE — Pistes de débogage :")
      print("  1. La capacité totale installée couvre-t-elle le pic de demande ?")
      total_capa = sum(g['p_nom'] for g in generators if 'p_nom' in g)
      max_demand = eraa_dataset.demand[country].max().values[0]
      print(f"     Demande max observée : {max_demand:.0f} MW")
      print(f"     Capacité totale installée : {total_capa:.0f} MW")
      print("  2. failure_power_capa est-il assez grand ?")
      print("  3. Les contraintes sur les stocks (hydro, batteries) sont-elles cohérentes ?")
      print("  4. La période simulée contient-elle bien des données ERAA ?")
      pypsa_model.plot_installed_capas(country=country,
                                       year=uc_run_params.selected_target_year,
                                       toy_model_output=True)
  ```
- Reproduire le même diagnostic dans `my_little_europe_lt_uc.py` (fonction `save_data_and_fig_results`, bloc `else` ligne ~213).
  (OB, 4/4/2026, commit 2d3004c3) TODO: tester/affiner calcul de la capa max (avec FC EnR moyen pour les capas EnR ?)
---

### 🟠 Priorité 2 — Impact Fort, Effort Raisonnable

#### P2-A : `README.md` — Manque de structure et de quickstart

Le README commence directement par les requirements sans expliquer ce qu'est le projet ni comment il est organisé. La section "Run locally" est dépréciée (lien vers PyCharm 2024.2.3 hardcodé). La section "Setting up Pycharm" contient littéralement `TO COME`.

- **Effort** : 2-3h
- **Sections à ajouter ou corriger** :
  1. En-tête : 3-4 lignes expliquant le projet (quoi, qui, pourquoi PyPSA + ERAA)
  2. "Structure du projet" : tableau court avec le rôle de chaque dossier (`/input`, `/output`, `/doc`, `/include`, `/utils`, `/data`, `/toy_model_params`)
  3. "Guide de démarrage rapide" : 3 étapes numérotées (ouvrir Codespace → lancer `my_toy_ex_italy.py` → lire le résultat dans `/output`)
  4. Supprimer ou compléter la section PyCharm (`TO COME` est inacceptable dans un README étudiant)
  5. Mettre à jour les screenshots si les noms de projets GitHub Classroom ont changé (TODO M2)

---

#### P2-B : `elec-europe_params_to-be-modif.json` — Trop complexe pour l'étudiant

Ce fichier mélange des paramètres simples (`selected_climatic_year`, `failure_penalty`) avec 23 entrées `interco_capas_tb_overwritten` et une structure `extra_params/max_co2_emis_constraints` avancée. Un étudiant débutant ne sait pas quoi toucher et risque de tout casser.

- **Effort** : 1-2h
- **Action** : Séparer les responsabilités :
  - Garder dans ce fichier uniquement les 5-6 paramètres que l'étudiant est censé modifier :
    `selected_climatic_year`, `selected_countries`, `selected_target_year`, `uc_period_start`, `uc_period_end`, `failure_penalty`
  - Déplacer `interco_capas_tb_overwritten` et `extra_params` dans un fichier `elec-europe_params_advanced.json` séparé, chargé optionnellement
  - Ajouter dans la documentation le sens physique de chaque paramètre (ex : `failure_penalty` = coût de la défaillance en €/MWh, typiquement 10 000 à 100 000)

---

#### P2-C : `devcontainer.json` — Image Docker trop lourde

`mcr.microsoft.com/devcontainers/universal:2` fait environ 10 Go et contient des dizaines d'outils inutiles (Go, Java, Ruby, Node...). Le build du Codespace est inutilement long pour les étudiants, surtout en début de session.

- **Effort** : 1-2h (test de build inclus)
- **Action** :
  ```json
  {
    "image": "mcr.microsoft.com/devcontainers/python:3.11",
    "postCreateCommand": "pip install --user -r requirements.txt",
    "waitFor": "postCreateCommand",
    "customizations": {
      "vscode": {
        "extensions": [
          "ms-python.python",
          "ms-python.vscode-pylance",
          "streetsidesoftware.code-spell-checker",
          "mechatroner.rainbow-csv",
          "ms-toolsai.jupyter"
        ]
      }
    }
  }
  ```
- L'image `python:3.11` fait ~1.5 Go et contient exactement ce dont le projet a besoin.
- `"waitFor": "postCreateCommand"` évite que l'étudiant lance le code avant que les packages soient installés.

---

#### P2-D : `TODO.md` — Inadapté comme outil de suivi

`TODO.md` contient 100+ items, mélange bugs/features/questions rhétoriques, certains sont probablement résolus (non marqués), et des références croisées opaques (`M6` → "Voir TODO[CR]" — introuvable dans le fichier).

- **Effort** : 2-3h
- **Action** (ne pas tout migrer vers GitHub Issues : trop long) :
  1. Ajouter un header avec 3 statuts : `[DONE]`, `[IN PROGRESS]`, `[TODO]`
  2. Supprimer les items purement rhétoriques ou résolus
  3. Résoudre les références croisées cassées
  4. Migrer vers GitHub Issues **uniquement** les 5-6 bugs actifs les plus critiques (P1-B en particulier)

---

### 🟡 Priorité 3 — Dette Technique à Adresser dans la Durée

#### P3-A : Absence totale de tests automatisés

Aucun fichier `test_*.py`, pas de dossier `tests/`. Toute modification du code par un enseignant ou TA est un saut dans le vide. Le PLAN.md le mentionne correctement (3.1) mais le classe trop bas.

- **Effort** : 4-6h pour une base minimale
- **Conseil** : Commencer par 2 tests seulement, sans dépendance au solver Gurobi :
  ```python
  # tests/test_data_reading.py
  from include.dataset import get_demand_data
  from datetime import datetime

  def test_get_demand_data_returns_valid_dataframe():
      df = get_demand_data(
          folder="data/ERAA_2023-2/demand",
          file_suffix="italy_2025",
          climatic_year=1989,
          period=(datetime(1900, 1, 1), datetime(1900, 1, 8))
      )
      assert "date" in df.columns
      assert len(df) == 7 * 24  # 7 jours, horaire

  # tests/test_toy_model_run.py
  import subprocess, sys

  def test_italy_toy_model_runs_without_crash():
      result = subprocess.run(
          [sys.executable, "my_toy_ex_italy.py"],
          capture_output=True, text=True, timeout=120
      )
      assert result.returncode == 0, f"Stderr:\n{result.stderr}"
  ```
- Lancer avec : `pytest tests/ -v`

---

#### P3-B : Migration PyPSA 0.35.1 → 1.0 (TODO M1)

PyPSA 1.0 introduit des changements d'API incompatibles notamment sur `optimize`, `committable`, et la gestion des `Store` pour l'hydro. La dette s'accumule à chaque nouvelle version.

- **Effort** : 8-16h — non trivial
- **Conseil** : Ne pas faire ça en cours d'année scolaire.
  1. Créer une branche `feature/pypsa-1.0`
  2. Mettre en place P3-A (tests) sur `main` d'abord
  3. Migrer sur la branche en se référant au [guide de migration PyPSA](https://pypsa.readthedocs.io/en/latest/whatsnew.html)
  4. Merger uniquement si tous les tests passent

---

#### P3-C : `dataset.py` — Monolithe de 784 lignes

784 lignes qui mélangent lecture de fichiers CSV, filtrage temporel, agrégation, et préparation pour PyPSA. Le PLAN.md propose une bonne direction (2.1) mais sans prérequis.

- **Prérequis absolu** : P3-A (tests) avant de toucher à ce fichier — sans filet de sécurité, le risque de régression est trop élevé
- **Effort réel** : 6-10h avec tests en place
- **Ordre conseillé** : extraire d'abord `get_demand_data` (déjà en dehors de la classe), puis les autres fonctions `get_*` de niveau module, et enfin alléger la classe `Dataset` elle-même

---

#### P3-D : Absence de CI GitHub Actions

Aucun workflow `.github/workflows/`. Sans intégration continue, un commit cassant le code n'est détecté que quand un étudiant tombe dessus le jour J.

- **Effort** : 2-3h
- **Action** : Créer `.github/workflows/ci.yml` :
  ```yaml
  name: CI
  on: [push, pull_request]
  jobs:
    test:
      runs-on: ubuntu-latest
      steps:
        - uses: actions/checkout@v4
        - uses: actions/setup-python@v5
          with:
            python-version: "3.11"
        - run: pip install -r requirements.txt
        - run: pytest tests/ -v
  ```
- À faire après P3-A (sinon la CI ne sert à rien)

---

## Résumé Priorisé avec Estimations d'Effort

| Priorité | Item | Fichier(s) concerné(s) | Effort | Impact |
|---|---|---|---|---|
| 🔴 P1-A | Épingler toutes les versions | `requirements.txt` | 1h | Reproductibilité |
| 🔴 P1-B | Corriger incohérence `wind_onshore` | `common/constants/prod_types.py`, CSV, JSON | 2-4h | Bug silencieux |
| 🔴 P1-C | Message d'aide infaisabilité | `my_toy_ex_italy.py`, `my_little_europe_lt_uc.py` | 2-3h | Expérience étudiante |
| 🟠 P2-A | README : quickstart + structure | `README.md` | 2-3h | Onboarding étudiant |
| 🟠 P2-B | Simplifier JSON params étudiant | `input/long_term_uc/elec-europe_params_to-be-modif.json` | 1-2h | Lisibilité |
| 🟠 P2-C | Devcontainer image allégée | `.devcontainer/devcontainer.json` | 1-2h | Vitesse build |
| 🟠 P2-D | Nettoyer `TODO.md` | `TODO.md` | 2-3h | Maintenabilité |
| 🟡 P3-A | Tests automatisés (base minimale) | nouveau dossier `tests/` | 4-6h | Filet de sécurité |
| 🟡 P3-D | CI GitHub Actions | nouveau `.github/workflows/ci.yml` | 2-3h | Maintenabilité |
| 🟡 P3-B | Migration PyPSA 1.0 | `requirements.txt`, `include/`, `utils/` | 8-16h | Longévité |
| 🟡 P3-C | Refactoring `dataset.py` | `include/dataset.py` | 6-10h | Maintenabilité |

**Effort total P1 + P2** : ~11-17h pour un développeur intermédiaire, réalisable en 2-3 jours de travail.  
**Effort total P3** : ~20-35h supplémentaires, à étaler sur plusieurs semaines hors période de cours.

---

## Ce que le PLAN.md devrait retirer ou déprioriser

- **Retirer** la proposition 2.2 (migrer toy model vers JSON) : coût élevé, bénéfice discutable, risque de confusion pour les étudiants
- **Déprioriser** la migration TODO → GitHub Issues (3.2) : 0 impact étudiant
- **Ajouter** les items P1-A, P1-B, P2-C, P2-D, P3-D qui sont absents du plan actuel
- **Remonter** P3-A (tests) en priorité 2, car c'est un prérequis pour P3-B et P3-C en sécurité
