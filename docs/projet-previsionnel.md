# Guide : Créer un projet prévisionnel

## Accès à la fonctionnalité

### Prérequis
- Être administrateur d'au moins une entreprise
- Accès à l'interface d'administration Django

### Navigation
1. Se connecter à l'interface d'administration : `/configuration/`
2. Dans la section "White Rabbit", cliquer sur "Projets prévisionnels"
3. Cliquer sur "Ajouter Projet prévisionnel"

## Création d'un projet prévisionnel

### Étape 1 : Informations du projet

Remplir les champs obligatoires et optionnels :

**Champs obligatoires :**
- **Nom** : Nom du projet prévisionnel
- **Entreprise** : Sélectionner l'entreprise (limitée aux entreprises que vous administrez)
- **Date de début** : Date prévue de début du projet (obligatoire)
- **Date de fin** : Date prévue de fin du projet (obligatoire)

**Champs optionnels mais recommandés :**
- **Catégorie** : Type de projet (Client, Interne, etc.)
- **Notes** : Description ou commentaires sur le projet
- **Jours prévus** : Nombre total de jours estimés pour le projet
- **Prix total de vente** : Montant prévu du projet en € HT

### Étape 2 : Affectation des employés

Dans la section "Affectations d'employés" :

1. **Sélection de l'employé** : 
   - Choisir parmi les employés de l'entreprise sélectionnée
   - Seuls les employés de la même entreprise que le projet sont disponibles

2. **Dates d'affectation** (optionnelles) :
   - **Date de début** : Si différente de la date de début du projet
   - **Date de fin** : Si différente de la date de fin du projet
   - **⚠️ Logique d'affectation** : Si les dates d'affectation sont vides, l'employé sera considéré comme affecté au projet pendant toute la durée du projet prévisionnel (de la date de début à la date de fin du projet)

3. **Jours estimés** : 
   - Nombre de jours prévus pour cet employé sur ce projet
   - ⚠️ **Important** : Le total des jours assignés ne doit pas dépasser le nombre de jours prévus du projet

### Étape 3 : Sauvegarde

Cliquer sur "Enregistrer" ou "Enregistrer et continuer les modifications"

## Visualisation

### Dans l'interface de disponibilité

Les projets prévisionnels apparaissent :
- Dans une section séparée avec un fond vert
- Avec un toggle pour les masquer/afficher
- Avec recalcul automatique des disponibilités

### Informations affichées
- Nom du projet et période
- Employés assignés avec leurs jours estimés
- Impact sur la disponibilité de chaque employé

## Règles de gestion des dates d'affectation

### Affectations sans dates spécifiées
Lorsqu'une affectation d'employé est créée **sans date de début ni date de fin** :
- L'affectation couvre automatiquement **toute la durée du projet prévisionnel**
- L'employé est considéré comme disponible sur ce projet de la date de début du projet jusqu'à sa date de fin
- Cette logique s'applique dans l'interface de disponibilité pour calculer la charge de travail

### Affectations avec dates partielles
- **Si seule la date de début est spécifiée** : l'affectation commence à cette date et se termine à la date de fin du projet
- **Si seule la date de fin est spécifiée** : l'affectation commence à la date de début du projet et se termine à la date spécifiée

### Contraintes de validation
- Les dates d'affectation doivent être comprises dans la période du projet prévisionnel
- La date de début d'affectation ne peut pas être postérieure à la date de fin d'affectation
- Un employé ne peut être affecté qu'à un projet de son entreprise
