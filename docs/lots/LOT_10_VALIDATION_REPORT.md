# Lot 10 — Rapport de validation et audit final

- **Lot :** 10 — Source portfolio runtime, backfill, fraîcheur et santé
- **Issue :** #29
- **Pull request :** #30
- **Branche :** `agent/source-portfolio-runtime`
- **Version :** `0.11.0`
- **SHA fonctionnel validé :** `6547a5f86217c9f20c7069eaab106981582e9f83`
- **CI de référence :** GitHub Actions run `31009515693`
- **Statut :** `IMPLEMENTED_VALIDATED`
- **Date de validation :** 2026-08-05

## 1. Résumé de livraison

Le lot 10 construit le plan de contrôle commun des sources au-dessus du scheduler durable existant. Il ne crée pas un second moteur de collecte : il ajoute un catalogue machine-readable, des capacités d’adaptateurs, des partitions de backfill persistantes, une projection de santé, des garde-fous quota/coût, des baselines de qualité, des événements historiques immuables et des hooks de valeur/ablation.

Le lot comprend également un adaptateur synthétique de référence sans réseau et une validation bout en bout du véritable adaptateur officiel CISA KEV avec transport HTTP simulé localement.

## 2. Résultats CI du SHA fonctionnel

Le SHA `6547a5f86217c9f20c7069eaab106981582e9f83` a passé l'intégralité des contrôles :

- audit de cohérence des dépendances Python : vert ;
- audit de sécurité `pip-audit` : vert ;
- Ruff : vert ;
- Mypy strict : vert ;
- contrats d'architecture et de release : verts ;
- migrations `upgrade head → downgrade base → upgrade head` : vertes ;
- suite backend : **528 tests réussis**, **0 échec**, **0 erreur**, **0 test ignoré** ;
- couverture lignes : **94,45 %** ;
- couverture branches : **82,23 %** ;
- seuil de couverture requis : **90 %**, respecté ;
- audit npm : vert ;
- typecheck frontend : vert ;
- build frontend : vert.

Les rapports JUnit et XML de couverture sont publiés par la CI dans l'artefact `backend-test-diagnostics`.

## 3. Audit des exigences fonctionnelles

### 3.1 Catalogue et capacités

- catalogue YAML machine-readable pour toutes les sources du portefeuille ;
- manifests d'adaptateurs versionnés ;
- modes déclarés : backfill historique, curseur incrémental, rafraîchissement conditionnel, lookup entité et priorité ;
- capacités de correction, tombstone et rétraction explicites ;
- candidats importés strictement non exécutables ;
- échec de démarrage lorsqu'une source statiquement exécutable ne possède pas d'adaptateur réel ;
- activation conditionnelle des sources ATS et d'identité uniquement lorsqu'une cible runtime existe.

### 3.2 Backfill durable

- partitions persistantes et idempotentes ;
- bornes et curseurs enregistrés ;
- états `pending`, `running`, `paused`, `failed`, `completed`, `cancelled` ;
- reprise avec curseur conservé ;
- maximum de cinq tentatives ;
- arrêt immédiat d'une erreur non retryable ;
- pause, reprise et annulation auditables ;
- état de santé fidèle, sans backfill artificiel lorsqu'aucune partition n'existe ;
- worker historique réellement branché au runtime ;
- priorité donnée à la file incrémentale, puis traitement historique lorsque cette file est vide ;
- backfill raw-only : aucune projection commerciale ou identité dérivée n'est créée pendant l'import historique.

### 3.3 Fraîcheur, quota et coût

- états `fresh`, `aging`, `stale_refresh_queued`, `source_unavailable`, `authorization_expired`, `quota_exhausted`, `cost_budget_exhausted`, `historical_only` ;
- blocage avant tout appel fournisseur lorsque l'autorisation est expirée, le quota est nul ou le prochain appel dépasserait le budget ;
- coût par requête issu du manifeste ;
- coût mensuel persistant ;
- fenêtre de coût remise à zéro au changement de mois ;
- quota existant conservé lorsqu'un fournisseur ne publie pas de nouvelle valeur ;
- télémétrie quota/coût remontée par `AdapterCollectionBatch`.

### 3.4 Santé et qualité des données

- intégration avec le circuit breaker existant, sans mécanisme concurrent ;
- dernière tentative, dernier succès, dernier enregistrement source et erreurs persistés ;
- baselines persistantes de volume, population des champs et empreintes de schéma ;
- phase d'apprentissage contrôlée sur trois échantillons ;
- EWMA pour les valeurs de référence ;
- détection de dérive avant toute modification de baseline ;
- une réponse `not modified` ne modifie pas la baseline et ne produit pas de faux état anormal ;
- les échantillons anormaux ne contaminent pas automatiquement la référence.

### 3.5 Corrections et convergence

- observations brutes immuables ;
- actions `upsert`, `correction`, `tombstone`, `retraction` ;
- relation `supersedes_observation_id` pour les mutations ;
- reducer canonique ordonné par temps fournisseur effectif ;
- même état final quel que soit l'ordre d'arrivée backfill/incrémental ;
- replay idempotent.

### 3.6 Valeur commerciale et ablation

- événement de contribution idempotent par source, exécution et mode ;
- mesures : exécutions, exécutions modifiées, observations, projections commerciales, projections d'identité et coût ;
- agrégation par source ;
- recalcul du portefeuille en excluant une source pour les analyses d'ablation ;
- les backfills enregistrent explicitement zéro projection dérivée.

### 3.7 API, interface et exploitation

- API de contrôle protégée par un jeton distinct des secrets fournisseurs ;
- aucun fallback de jeton de développement en production ;
- interface Sources : état catalogue, fraîcheur, schéma, volume, champs, circuit, backfill, quota, coût et fenêtre mensuelle ;
- actions protégées : priorité, pause, reprise, désactivation, réactivation et annulation du backfill ;
- cycle de désactivation réversible ;
- une désactivation explicite n'est jamais annulée par la réconciliation runtime ;
- les sources gérées par des cibles ne peuvent pas contourner la réconciliation avec un bouton générique.

### 3.8 Gouvernance et sécurité

- aucune source candidate ne peut être planifiée ou exécutée ;
- LinkedIn, BrixHub et les imports de catalogues restent non exécutables sans gouvernance explicite ;
- aucune création de compte, contournement de CAPTCHA/MFA/KYC ou collecte privée n'est introduit ;
- aucun secret fournisseur brut n'est stocké ni exposé au navigateur ;
- clés étrangères et suppression en cascade contrôlée pour les données du portefeuille ;
- migrations réversibles ;
- artefacts de diagnostic CI conservés sept jours.

## 4. Preuves verticales

Les tests couvrent notamment :

1. `job → worker → observation brute → checkpoint → santé → événement de valeur` avec l'adaptateur synthétique ;
2. chaîne officielle CISA KEV avec vraie politique, vrai adaptateur, vrai scheduler/worker et `httpx.MockTransport`, sans réseau externe ;
3. `partition historique → adaptateur → observation brute → curseur → santé`, sans signal commercial ;
4. pause ou expiration empêchant la création de jobs ;
5. annulation d'un job déjà en file avant l'appel fournisseur ;
6. quota nul et budget dépassé empêchant l'exécution ;
7. reprise au changement de mois ;
8. correction/tombstone/rétraction convergeant après ordre d'arrivée inversé ;
9. baseline stable puis dérive de schéma, volume et champs ;
10. ablation d'une source recalculant les métriques du portefeuille.

## 5. Audit de propreté

- aucun second scheduler ou circuit breaker dupliqué ;
- composants séparés par responsabilité ;
- limites d'architecture respectées, dont fonctions ≤ 120 lignes et modules ≤ 400 lignes ;
- façade publique stable pour le module `source_portfolio` ;
- typage strict et validation des entrées ;
- actions opérateur auditables ;
- idempotence sur jobs, partitions, observations et événements de valeur ;
- aucune prétention de validation réseau réelle : le test officiel CISA utilise un transport local déterministe.

## 6. Décision de livraison

Les exigences du lot 10 sont implémentées et validées. La PR peut être passée en revue puis fusionnée uniquement après une dernière CI verte sur le commit documentaire contenant ce rapport.
