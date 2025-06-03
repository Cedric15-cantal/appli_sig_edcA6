**Objectif** : Calculer un itinéraire optimal depuis un point donné jusqu’au défibrillateur le plus proche, en utilisant le réseau routier.

## 1. Sélection des données de la table `voirie`

```sql
SELECT fid, geom, id_troncon, code_insee, street, type
	FROM datas.voirie;
```

**Commentaire** :  
Cette requête sélectionne des colonnes spécifiques de la table `datas.voirie`, qui contient des données sur les tronçons de voirie (routes, chemins, etc.).  
- `fid` : Identifiant unique de chaque tronçon.  
- `geom` : Colonne géométrique contenant les géométries (lignes représentant les routes) au format spatial, probablement en projection EPSG:3857 (Web Mercator).  
- `id_troncon`, `code_insee`, `street`, `type` : Métadonnées associées aux tronçons (identifiant du tronçon, code INSEE de la commune, nom de la rue, type de voie).  
**Objectif** : Explorer ou vérifier le contenu de la table pour s'assurer que les données sont correctes avant de procéder à des analyses plus complexes.

## 2. Analyse des types de géométries

```sql
-- Afficher les types de géométrie de la voirie
SELECT distinct ST_GeometryType(geom), ST_NumGeometries(geom)
	FROM datas.voirie;
```

**Commentaire** :  
Cette requête examine les types de géométries et le nombre de géométries dans la colonne `geom` de la table `datas.voirie`.  
- `ST_GeometryType(geom)` : Fonction PostGIS qui retourne le type de géométrie (par exemple, `ST_LineString` pour une ligne simple ou `ST_MultiLineString` pour plusieurs lignes).  
- `ST_NumGeometries(geom)` : Retourne le nombre de géométries dans un objet géométrique, utile pour les géométries complexes comme `MultiLineString`.  
- `DISTINCT` : Évite les doublons pour ne lister que les combinaisons uniques de type et de nombre de géométries.  
**Objectif** : Identifier la structure des données spatiales (par exemple, lignes simples ou multilignes) pour s'assurer que les géométries sont cohérentes avant traitement.

## 3. Suppression des géométries nulles

```sql
-- Supprimer les géométries nulles
DELETE FROM datas.voirie
	WHERE ST_GeometryType(geom) is null;
```

**Commentaire** :  
Cette requête supprime les enregistrements de la table `datas.voirie` où la colonne `geom` ne contient pas de géométrie valide (c'est-à-dire où `ST_GeometryType(geom)` retourne `NULL`).  
- **Pourquoi ?** Les géométries `NULL` peuvent causer des erreurs dans les analyses spatiales ou indiquer des données corrompues.  
- **Impact** : Nettoyage des données pour garantir que seules les géométries valides sont utilisées dans les étapes suivantes.  

## 4. Vérification des fonctions `ST_Dump` et `ST_LineMerge`

```sql
-- Vérification des fonctions ST_Dump et ST_LineMerge
-- Extraire les voiries du quartier 5
with req as (SELECT voirie.fid,
(st_dump(voirie.geom)).geom::geometry(linestring,3857) as geom_dump, 
ST_LineMerge(voirie.geom)::geometry(linestring,3857) as geom_merge, 
id_troncon, code_insee, street, type
	FROM datas.voirie
	JOIN datas.quartiers
	ON st_intersects(voirie.geom,quartiers.geom)
		WHERE quartier=5)
SELECT *
FROM req
WHERE st_disjoint(geom_dump,geom_merge);
```

**Commentaire** :  
Cette requête complexe teste les fonctions PostGIS `ST_Dump` et `ST_LineMerge` tout en extrayant les tronçons de voirie situés dans le quartier 5. Décomposons-la :  

1. **Sous-requête `WITH req AS`** :  
   - Crée une table temporaire `req` pour stocker les résultats intermédiaires.  
   - Sélectionne les colonnes `fid`, `id_troncon`, `code_insee`, `street`, `type` de la table `datas.voirie`.  
   - `ST_Dump(voirie.geom).geom` : Décompose les géométries complexes (comme `MultiLineString`) en géométries simples (`LineString`). Le résultat est casté en `geometry(linestring,3857)` pour garantir que les géométries sont des lignes simples dans la projection EPSG:3857.  
   - `ST_LineMerge(voirie.geom)` : Fusionne les segments d'une géométrie `MultiLineString` en une seule `LineString` si les segments sont connectés. Également casté en `geometry(linestring,3857)`.  
   - **Jointure spatiale** : La clause `JOIN datas.quartiers ON st_intersects(voirie.geom, quartiers.geom)` sélectionne uniquement les tronçons de voirie qui intersectent géométriquement le quartier 5 (condition `WHERE quartier=5`).  

2. **Requête principale** :  
   - La clause `WHERE st_disjoint(geom_dump, geom_merge)` filtre les résultats pour ne retourner que les lignes où les géométries issues de `ST_Dump` et `ST_LineMerge` sont disjointes (c'est-à-dire qu'elles ne partagent aucun point commun).  
   - **Pourquoi ?** Cela permet de vérifier les différences entre `ST_Dump` (décomposition en segments) et `ST_LineMerge` (fusion des segments connectés). Si les géométries sont disjointes, cela peut indiquer des incohérences dans les données ou des comportements inattendus des fonctions.  

**Objectif** : Tester les fonctions PostGIS et identifier les tronçons de voirie dans le quartier 5 tout en vérifiant la cohérence des géométries.

## 5. Création d'une table pour les voiries du quartier 5

```sql
-- Extraire les voiries du quartier 5 dans une table
CREATE TABLE zone_etude.voirie AS
SELECT voirie.fid,
(st_dump(voirie.geom)).geom::geometry(linestring,3857) as geom,  
id_troncon, code_insee, street, type
	FROM datas.voirie
	JOIN datas.quartiers
	ON st_intersects(voirie.geom,quartiers.geom)
		WHERE quartier=5;
```

**Commentaire** :  
Cette requête crée une nouvelle table `zone_etude.voirie` contenant les tronçons de voirie situés dans le quartier 5.  
- Similaire à la requête précédente, elle utilise `ST_Dump` pour décomposer les géométries complexes en `LineString` simples, castées en EPSG:3857.  
- La jointure spatiale `st_intersects` garantit que seuls les tronçons intersectant le quartier 5 sont inclus.  
- **Différence avec la requête précédente** : Les résultats sont stockés dans une table permanente pour des analyses ultérieures, plutôt que d'être simplement affichés.  
**Objectif** : Créer une table dédiée pour les analyses spatiales sur les tronçons du quartier 5.

## 6. Ajout d'une clé primaire

```sql
-- Ajout clé primaire
ALTER TABLE zone_etude.voirie
 ADD CONSTRAINT pk_voirie primary key (fid);
 -- En faire une identity
```

**Commentaire** :  
- La commande `ALTER TABLE` ajoute une contrainte de clé primaire nommée `pk_voirie` sur la colonne `fid` de la table `zone_etude.voirie`. Cela garantit que chaque valeur de `fid` est unique et non nulle.  
- La ligne de commentaire `--en faire une identity` indique une intention de transformer la colonne `fid` en une colonne avec la propriété `IDENTITY` (génération automatique d'identifiants). Cependant, le code SQL correspondant n'est pas fourni. Une commande possible serait :  
  ```sql
  ALTER TABLE zone_etude.voirie
  ALTER COLUMN fid ADD GENERATED ALWAYS AS IDENTITY;
  ```  
**Objectif** : Renforcer l'intégrité des données avec une clé primaire. La mention d'`IDENTITY` suggère une volonté d'automatiser la génération des identifiants, mais cela n'est pas implémenté ici.

## 7. Création d'une table pour les défibrillateurs du quartier 5

```sql
-- Récupération des défibrillateurs du quartier 5
CREATE TABLE zone_etude.defibr AS
SELECT defib.*
FROM datas.defibrillateurs defib
JOIN datas.quartiers
	ON st_intersects(defib.geom,quartiers.geom)
		WHERE quartier=5;
ALTER TABLE zone_etude.defibr
ADD CONSTRAINT pk_defibr primary key (fid);
```

**Commentaire** :  
- **Création de la table** : Cette requête crée une table `zone_etude.defibr` contenant les défibrillateurs situés dans le quartier 5.  
  - `SELECT defib.*` : Sélectionne toutes les colonnes de la table `datas.defibrillateurs`.  
  - La jointure spatiale `st_intersects(defib.geom, quartiers.geom)` filtre les défibrillateurs dont la géométrie (probablement des points) intersecte le quartier 5.  
- **Ajout de la clé primaire** : Une contrainte de clé primaire `pk_defibr` est ajoutée sur la colonne `fid` pour garantir l'unicité des identifiants.  
**Objectif** : Stocker les données des défibrillateurs du quartier 5 dans une table dédiée pour des analyses ultérieures, avec une clé primaire pour l'intégrité des données.

## 8. Ajout de tronçons reliant les défibrillateurs aux routes

```sql
-- Ajout des tronçons
INSERT INTO zone_etude.voirie(geom)
WITH req AS (-- Ajout d'un rang en fonction de la distance du point aux tronçon de route pour ne sélectionner que le tronçon le plus proche
             SELECT r.fid AS id_troncon,
                    defibr.fid AS id_defibr,
                    r.geom AS geomr,
                    defibr.geom AS geomdefibr,
                    rank() OVER (PARTITION BY defibr.fid ORDER BY (min(r.geom <-> defibr.geom))) AS rang
                 FROM zone_etude.voirie r
                     JOIN zone_etude.defibr ON st_dwithin(r.geom, defibr.geom, 500::double precision)
                  GROUP BY r.fid, defibr.fid, r.geom, defibr.geom
                  ORDER BY r.fid
                )
         SELECT st_shortestline(geomr, geomdefibr)::geometry(LineString,3857) AS geom
           FROM req
          WHERE req.rang = 1
          ORDER BY 1;
```

**Commentaire** :  
Cette requête insère de nouveaux tronçons dans la table `zone_etude.voirie`, représentant les lignes les plus courtes entre chaque défibrillateur et le tronçon de voirie le plus proche dans un rayon de 500 mètres. Décomposons-la :  

1. **Sous-requête `WITH req AS`** :  
   - Jointure entre `zone_etude.voirie` (tronçons) et `zone_etude.defibr` (défibrillateurs) avec `st_dwithin(r.geom, defibr.geom, 500)` pour ne considérer que les tronçons à moins de 500 mètres d’un défibrillateur.  
   - `rank() OVER (PARTITION BY defibr.fid ORDER BY (min(r.geom <-> defibr.geom)))` : Attribue un rang à chaque tronçon par rapport à chaque défibrillateur, en fonction de la distance (`<->` est l’opérateur de distance de PostGIS). Le tronçon le plus proche reçoit le rang 1.  
   - Les colonnes sélectionnées incluent `id_troncon` (fid du tronçon), `id_defibr` (fid du défibrillateur), `geomr` (géométrie du tronçon), `geomdefibr` (géométrie du défibrillateur), et `rang`.  

2. **Requête principale** :  
   - `st_shortestline(geomr, geomdefibr)` : Calcule la ligne la plus courte entre le tronçon et le défibrillateur.  
   - Castée en `geometry(LineString,3857)` pour garantir le type et la projection.  
   - `WHERE req.rang = 1` : Ne sélectionne que le tronçon le plus proche pour chaque défibrillateur.  
   - `INSERT INTO zone_etude.voirie(geom)` : Insère ces lignes dans la colonne `geom` de la table `zone_etude.voirie`.  

**Objectif** : Ajouter des tronçons reliant les défibrillateurs aux routes les plus proches, probablement pour modéliser des chemins d’accès.

## 9. Création des nœuds pour le réseau

```sql
-- Ajout des nœuds
SELECT pgr_nodeNetwork('zone_etude.voirie', 0.001, 'fid','geom');
SELECT * FROM zone_etude.voirie_noded;
```

**Commentaire** :  
- `pgr_nodeNetwork` : Fonction de l’extension **pgRouting** qui segmente les tronçons de la table `zone_etude.voirie` en créant des nœuds aux intersections et aux extrémités des lignes.  
  - Paramètres :  
    - `'zone_etude.voirie'` : Table source.  
    - `0.001` : Tolérance (en mètres pour EPSG:3857) pour détecter les intersections.  
    - `'fid'` : Colonne d’identifiant.  
    - `'geom'` : Colonne géométrique.  
  - Résultat : Crée une nouvelle table `zone_etude.voirie_noded` avec des tronçons segmentés et des nœuds.  
- `SELECT * FROM zone_etude.voirie_noded` : Affiche le contenu de la table générée pour vérification.  
**Objectif** : Préparer les données pour une analyse topologique (par exemple, calcul de chemins).

## 10. Création de la topologie

```sql
-- Topologie
SELECT pgr_createTopology('zone_etude.voirie_noded',0.001,'geom');
SELECT * FROM zone_etude.voirie_noded_vertices_pgr;
```

**Commentaire** :  
- `pgr_createTopology` : Crée une topologie pour la table `zone_etude.voirie_noded`.  
  - Ajoute les colonnes `source` et `target` (identifiants des nœuds aux extrémités de chaque tronçon).  
  - Crée une table `zone_etude.voirie_noded_vertices_pgr` contenant les nœuds du réseau (points aux extrémités et intersections).  
  - Paramètres : Tolérance de 0.001 et colonne géométrique `geom`.  
- `SELECT * FROM zone_etude.voirie_noded_vertices_pgr` : Affiche les nœuds générés pour vérification.  
**Objectif** : Construire une topologie réseau pour permettre des analyses de routage (par exemple, plus court chemin).

## 11. Analyse de la topologie

```sql
-- Vérification
SELECT pgr_analyzeGraph('zone_etude.voirie_noded',0.001,'geom');
```

**Commentaire** :  
- `pgr_analyzeGraph` : Analyse la topologie de la table `zone_etude.voirie_noded` pour détecter des problèmes (par exemple, nœuds isolés ou tronçons non connectés).  
- Retourne un rapport sur l’état du graphe (nœuds orphelins, connectivité, etc.).  
**Objectif** : Vérifier la qualité de la topologie avant de procéder à des calculs de routage.

## 12. Gestion des sens de circulation

```sql
-- Sens
ALTER TABLE zone_etude.voirie_noded ADD COLUMN dir varchar default('B');
SELECT pgr_analyzeOneway('zone_etude.voirie_noded',
  ARRAY['', 'B', 'TF'],
  ARRAY['', 'B', 'FT'],
  ARRAY['', 'B', 'FT'],
  ARRAY['', 'B', 'TF'],
  oneway:='dir');
SELECT * FROM zone_etude.voirie_noded_vertices_pgr;
```

**Commentaire** :  
1. **Ajout de la colonne `dir`** :  
   - Ajoute une colonne `dir` de type `varchar` avec la valeur par défaut `'B'` (probablement pour "bidirectionnel").  
   - Cette colonne indique le sens de circulation des tronçons (`B` pour bidirectionnel, `TF` pour "to-from", `FT` pour "from-to").  

2. **Analyse des sens uniques** :  
   - `pgr_analyzeOneway` : Analyse les règles de circulation à sens unique dans la table `zone_etude.voirie_noded`.  
   - Les paramètres `ARRAY['', 'B', 'TF']`, etc., définissent les valeurs autorisées pour les tronçons dans différentes directions (aller, retour, bidirectionnel).  
   - `oneway:='dir'` : Indique que la colonne `dir` contient les informations de sens.  
   - Cette fonction vérifie si le réseau respecte les règles de circulation.  

3. **Vérification des nœuds** :  
   - `SELECT * FROM zone_etude.voirie_noded_vertices_pgr` : Affiche à nouveau les nœuds pour vérifier les modifications apportées par l’analyse.  

**Objectif** : Ajouter des informations de sens de circulation et vérifier la cohérence du réseau pour le routage.

## 13. Calcul du coût des tronçons

```sql
-- Calcul du coût
ALTER TABLE zone_etude.voirie_noded
 add column cost float;
update zone_etude.voirie_noded 
  set cost=round(st_length(geom)::numeric,2);
```

**Commentaire** :  
- **Ajout de la colonne `cost`** : Crée une colonne `cost` de type `float` pour stocker le coût de chaque tronçon (souvent la longueur ou le temps de parcours).  
- **Mise à jour du coût** :  
  - `ST_Length(geom)` : Calcule la longueur de chaque tronçon en mètres (EPSG:3857).  
  - `round(..., 2)` : Arrondit la longueur à deux décimales.  
  - La colonne `cost` est mise à jour avec ces longueurs.  
**Objectif** : Préparer les données pour le calcul de chemins en attribuant un coût (longueur) à chaque tronçon.

## 14. Calcul d'un trajet avec Dijkstra

```sql
-- Trajet
SELECT seq, node, edge, geom
        FROM pgr_dijkstra(
                'SELECT id, source, target, cost FROM zone_etude.voirie_noded',
                1, 5, false
        ) JOIN zone_etude.voirie_noded ON voirie_noded.id=edge;
```

**Commentaire** :  
- `pgr_dijkstra` : Fonction pgRouting qui calcule le plus court chemin entre deux nœuds (ici, nœuds 1 et 5) en utilisant l’algorithme de Dijkstra.  
  - `'SELECT id, source, target, cost FROM zone_etude.voirie_noded'` : Définit le graphe avec les colonnes `id` (identifiant du tronçon), `source` et `target` (nœuds de départ et d’arrivée), et `cost` (coût du tronçon).  
  - `false` : Indique que le graphe n’est pas orienté (les tronçons sont bidirectionnels).  
- **Jointure** : Associe les résultats de `pgr_dijkstra` (séquence, nœuds, arêtes) à la table `zone_etude.voirie_noded` pour récupérer la géométrie (`geom`) des tronçons du chemin.  
- **Colonnes retournées** :  
  - `seq` : Ordre des tronçons dans le chemin.  
  - `node` : Nœud visité.  
  - `edge` : Identifiant du tronçon.  
  - `geom` : Géométrie du tronçon.  
**Objectif** : Calculer et afficher le plus court chemin entre les nœuds 1 et 5.

## 15. Association des nœuds aux défibrillateurs

```sql
-- Associer les nœuds des voies aux défibrillateurs
CREATE VIEW v_node_route_defibr as
  SELECT r.id, defibr.fid	  
    FROM zone_etude.voirie_noded_vertices_pgr r, zone_etude.defibr
          WHERE st_distance(r.the_geom, defibr.geom) = 0
      GROUP BY r.id, defibr.fid
     ORDER BY fid;
```

**Commentaire** :  
- Cette requête crée une vue `v_node_route_defibr` qui associe les nœuds du réseau routier (table `zone_etude.voirie_noded_vertices_pgr`) aux défibrillateurs (table `zone_etude.defibr`).  
- `st_distance(r.the_geom, defibr.geom) = 0` : Identifie les nœuds situés exactement au même endroit que les défibrillateurs (distance géométrique nulle).  
- `GROUP BY r.id, defibr.fid` : Évite les doublons dans les associations.  
- `ORDER BY fid` : Trie les résultats par identifiant de défibrillateur.  
**Objectif** : Créer une correspondance entre les nœuds du réseau routier et les défibrillateurs pour faciliter les calculs de routage impliquant les défibrillateurs.

## 16. Calcul d'un trajet vers un défibrillateur

```sql
-- Par rapport aux défibrillateurs
SELECT seq, node, edge, geom
        FROM pgr_dijkstra(
                'SELECT id, source, target, cost FROM zone_etude.voirie_noded',
  /* Départ : */  (SELECT id as id_depart
                   FROM zone_etude.voirie_noded_vertices_pgr
                     ORDER BY the_geom <-> ST_SetSRID(ST_Point(566582.08,6278704.89),3857) 
					 LIMIT 1),
  /* Arrivée : */  (SELECT routes_n.id as id_arrivee
                   FROM zone_etude.voirie_noded_vertices_pgr routes_n
                     join v_node_route_defibr as defibr_r on routes_n.id=defibr_r.id
					 where defibr_r.fid=(select fid 
									from zone_etude.defibr
									 ORDER BY geom <-> ST_SetSRID(ST_Point(566582.08,6278704.89),3857)
									 limit 1)
					 ), 
				false
        ) JOIN zone_etude.voirie_noded ON voirie_noded.id=edge;
```

**Commentaire** :  
Cette requête calcule le plus court chemin entre un point de départ donné et le défibrillateur le plus proche, en utilisant l’algorithme de Dijkstra. Décomposons-la :  

1. **Point de départ** :  
   - La sous-requête `(SELECT id as id_depart ...)` identifie le nœud du réseau le plus proche d’un point donné (coordonnées `566582.08, 6278704.89` en EPSG:3857).  
   - `ST_SetSRID(ST_Point(...), 3857)` : Crée un point géométrique avec la projection correcte.  
   - `ORDER BY the_geom <-> ... LIMIT 1` : Sélectionne le nœud le plus proche en utilisant l’opérateur de distance `<->`.  

2. **Point d’arrivée** :  
   - La sous-requête `(SELECT routes_n.id as id_arrivee ...)` identifie le nœud associé au défibrillateur le plus proche du point de départ.  
   - Utilise la vue `v_node_route_defibr` pour associer les nœuds aux défibrillateurs.  
   - La sous-requête imbriquée `(select fid ...)` trouve le défibrillateur le plus proche du point de départ.  

3. **Calcul du chemin** :  
   - `pgr_dijkstra` calcule le plus court chemin entre le nœud de départ et le nœud d’arrivée.  
   - `false` : Indique un graphe non orienté.  
   - La jointure avec `zone_etude.voirie_noded` récupère les géométries des tronçons du chemin.  