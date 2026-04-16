# Plan d'Amélioration du Projet

Ce document liste une série de recommandations pour améliorer la qualité, la robustesse et l'expérience pédagogique du projet. Les actions sont priorisées pour faciliter leur mise en œuvre.

L'objectif est de rendre le projet :
*   **Plus accessible** pour les étudiants débutants.
*   **Plus facile à comprendre** pour ceux qui souhaitent explorer le code.
*   **Plus robuste et maintenable** pour l'équipe enseignante.

---

### Axe 1 : Priorité Haute - Améliorations pour l'Expérience Étudiante

*Ces actions ont l'impact le plus direct sur la prise en main du projet par les étudiants.*

**1.1. Créer un Guide de Démarrage Rapide dans `README.md`**

*   **Justification** : La première impression est cruciale. Un étudiant doit pouvoir lancer une première simulation en quelques minutes pour se sentir en confiance. Le `README.md` actuel peut être rendu plus directif.
*   **Action** : Ajouter une section "🚀 Guide de Démarrage Rapide" en haut du `README.md` qui résume les 3 étapes pour démarrer : lancer Codespaces, exécuter le script d'exemple, et trouver les instructions du TP.
*   **Référence `TODO.md`** : `M2`

**1.2. Simplifier et Documenter les Fichiers de Paramètres (`.json`)**

*   **Justification** : Les fichiers JSON sont la principale interface de l'étudiant avec le modèle. Une structure complexe ou des noms de paramètres peu clairs sont une source de frustration et d'erreurs.
*   **Action** :
    1.  Ne laisser dans les fichiers `input/long_term_uc/countries/{country}.json` que les paramètres que les étudiants sont censés modifier.
    2.  Fournir des commentaires directement dans la documentation pour expliquer la *signification physique* de chaque paramètre (ex: `failure_penalty`).
    3.  Améliorer la documentation (`European-system_tutorial.md`) pour qu'elle se concentre sur l'impact de ces paramètres.
*   **Référence `TODO.md`** : `M13`, `E4`, `D4`

**1.3. Mieux Guider en Cas d'Erreur d'Optimisation (Infaisabilité)**

*   **Justification** : Obtenir une erreur "infeasible" est courant en modélisation, mais très déroutant pour un débutant. Le code peut transformer cette frustration en un exercice de débogage guidé.
*   **Action** : Dans les scripts principaux (ex: `my_toy_ex_italy.py`), après l'appel à `optimize_network`, ajouter un bloc `if/else` qui vérifie le statut de la solution. Si le statut n'est pas `optimal`, afficher des messages d'aide clairs et des pistes de correction. (Ex: "L'optimisation a échoué. Pistes possibles : 1. La capacité de production est-elle suffisante pour couvrir la demande ? 2. Les contraintes sur le stockage sont-elles trop restrictives ?").
*   **Référence `TODO.md`** : `M7`

---

### Axe 2 : Priorité Moyenne - Rendre le Code Plus Lisible et Modulaire

*Ces actions visent à réduire la complexité perçue du code et à faciliter sa maintenance.*

**2.1. Refactoriser le "Cœur" du Modèle (`include/dataset.py`)**

*   **Justification** : Le fichier `include/dataset.py` est très long (+600 lignes) et mélange plusieurs responsabilités (lecture des données, traitement, préparation pour PyPSA). Cela le rend difficile à lire, à déboguer et à faire évoluer.
*   **Action** : Diviser ce fichier en plusieurs modules plus petits et spécialisés. Par exemple :
    *   `include/readers.py` : Pour toutes les fonctions qui lisent les fichiers CSV (`get_demand_data`, etc.).
    *   `include/processors.py` : Pour les fonctions qui transforment les données (`calc_net_demand`, etc.).
    *   La classe `Dataset` orchestrerait les appels à ces modules, rendant son propre code plus clair.
*   **Effort** : Élevé.
*   **Exemple Concret** :
    1.  Créez un nouveau fichier `include/readers.py`.
    2.  Déplacez la fonction `get_demand_data` de `include/dataset.py` vers `include/readers.py`.
    3.  Dans `include/dataset.py`, importez et utilisez cette fonction :

    ```python
    # Dans include/dataset.py, au début du fichier
    from .readers import get_demand_data

    # ...

    # Dans la méthode get_countries_data de la classe Dataset
    if DATATYPE_NAMES.demand in dts_tb_read:
        # get demand
        current_df_demand = get_demand_data(folder=demand_folder, ...) # Appel à la fonction importée
    ```
    Répétez ce processus pour les autres fonctions de lecture (`get_res_capa_factors_data`, `get_installed_gen_capas_data`, etc.).
*   **Référence `TODO.md`** : `M17` (suggère l'utilisation d'outils pour le refactoring)

**2.2. Clarifier la Structure du Projet et les Approches de Paramétrage**

*   **Justification** : Les étudiants peuvent être perdus face à la multitude de fichiers. Il est important de leur indiquer où se concentrer. De plus, l'approche de paramétrage diffère entre le "toy model" (fichier Python) et le modèle européen (fichiers JSON), ce qui peut créer de la confusion.
*   **Action** :
    1.  Ajouter une section "Structure du Projet" dans le `README.md` qui explique le rôle de chaque dossier principal (`/input`, `/output`, `/doc`, `/data`, `/include`).
    2.  Faire converger le "toy model" vers une approche de paramétrage par fichier JSON, similaire au modèle européen, pour une expérience plus cohérente.
*   **Effort** : Moyen.
*   **Exemple Concret (pour le point 2)** : Actuellement, `toy_model_params/italy_parameters.py` contient les données des générateurs en dur. Modifiez la fonction `get_generators` pour qu'elle lise un fichier `italy_generators.json` :
    ```python
    # Dans toy_model_params/italy_parameters.py
    import json

    def get_generators_from_json(filepath: str) -> List[GENERATOR_DICT_TYPE]:
        with open(filepath, 'r') as f:
            generators_data = json.load(f)
        # ... (ajouter les données de séries temporelles comme les CF, qui ne peuvent pas être dans le JSON)
        return generators_data
    ```
    Le script `my_toy_ex_italy.py` appellerait alors cette nouvelle fonction. Cela harmonise la manière dont les étudiants interagissent avec les deux modèles.
*   **Référence `TODO.md`** : `M13`, `T3`

---

### Axe 3 : Priorité Basse - Robustesse à Long Terme et Fonctionnalités Avancées

*Ces actions consolident le projet sur le long terme et ouvrent la voie à des analyses plus poussées.*

**3.1. Mettre en Place des Tests Automatisés**

*   **Justification** : Pour garantir qu'une modification apportée au code ne casse pas une fonctionnalité existante. C'est un filet de sécurité indispensable pour la maintenance d'un projet utilisé sur plusieurs années.
*   **Action** : Introduire la librairie `pytest`. Créer un dossier `tests/` avec quelques tests de base :
    *   Un test qui lance `my_toy_ex_italy.py` et vérifie qu'il s'exécute jusqu'au bout sans erreur.
    *   Un test qui vérifie que la lecture des données de demande pour un pays renvoie un DataFrame avec le bon format.
*   **Effort** : Moyen.
*   **Exemple Concret** : Créez un fichier `tests/test_toy_model_run.py` :
    ```python
    import subprocess
    import sys

    def test_italy_toy_model_runs_successfully():
        """
        Exécute le script du modèle italien et vérifie qu'il se termine
        avec un code de sortie 0 (succès).
        """
        script_path = "my_toy_ex_italy.py"
        result = subprocess.run([sys.executable, script_path], capture_output=True, text=True)

        assert result.returncode == 0, f"Le script a échoué avec le code {result.returncode}.\nStderr: {result.stderr}"
    ```
    Vous pouvez lancer ce test depuis le terminal avec la commande `pytest`.
*   **Référence `TODO.md`** : `M17`

**3.2. Industrialiser la Gestion des Tâches (`TODO.md` -> GitHub Issues)**

*   **Justification** : Le fichier `TODO.md` est une excellente base, mais il n'est pas adapté au suivi et à la collaboration. Les "Issues" GitHub permettent d'assigner des tâches, de discuter de leur implémentation et de suivre leur progression.
*   **Action** : Migrer les points pertinents du `TODO.md` vers des "Issues" sur le dépôt GitHub du projet. Utiliser des labels (`bug`, `documentation`, `amélioration`) pour les organiser.
*   **Effort** : Faible.
*   **Exemple Concret** : Pour le point `M7` du `TODO.md` :
    *   **Créer une nouvelle Issue GitHub**
    *   **Titre** : `Améliorer le guidage en cas d'infaisabilité du modèle`
    *   **Description** :
        ```
        Lorsqu'une optimisation échoue (statut 'infeasible'), les étudiants sont démunis. Il faut intercepter cet état et afficher des messages d'aide pour les guider dans le débogage.

        Voir `PLAN.md`, point 1.3.
        ```
    *   **Labels** : `documentation`, `amélioration`, `student-facing`
*   **Référence `TODO.md`** : La première ligne du fichier le suggère.