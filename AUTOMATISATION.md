# NovaNic Studio — SoundCloud → GitHub Pages + Blogger 💜

Ce module complète le générateur d'articles existant.

## Ce qui est automatisé
- Le workflow GitHub Actions `soundcloud-sync.yml` vérifie la playlist publique toutes les **6 heures** environ (horaires indicatifs).
- Le **premier lancement** mémorise les chansons existantes, sans créer de vieux articles Blogger.
- Chaque nouvelle chanson est ajoutée au catalogue public `/chansons/`.
- Si les autorisations Blogger sont configurées, un article Blogger est également créé.
- Le suivi dans `chansons/state.json` évite normalement les doublons.
- Si Blogger n'est pas connecté, les nouvelles chansons attendent ; elles pourront être publiées après connexion.

## Activer GitHub Actions
1. Aller dans **Settings → Actions → General → Workflow permissions**.
2. Choisir **Read and write permissions** et enregistrer.
3. Aller dans **Actions → NovaNic - Synchroniser SoundCloud → Run workflow**.
4. Vérifier les logs du premier lancement.
5. Une fois terminé, le catalogue doit apparaître à : https://zlormann.github.io/novanic-studio/chansons/

Si l'extraction échoue, SoundCloud peut bloquer les accès automatisés ou modifier son site. Le script s'arrête sans effacer les chansons déjà enregistrées. L'outil `yt-dlp` est une dépendance externe.

## Activer Blogger sans Google Apps Script
La publication Blogger nécessite toujours l'API Blogger et l'autorisation du propriétaire du blog. **Ne jamais ajouter les secrets dans le code public ni les envoyer dans une conversation.**

1. Dans [Google Cloud Console](https://console.cloud.google.com/), activer **Blogger API v3** sur un projet.
2. Configurer l'écran de consentement OAuth et un client OAuth 2.0. Pour utiliser [OAuth Playground](https://developers.google.com/oauthplayground/) avec vos identifiants, créer un client de type Application Web et autoriser l'URI de redirection `https://developers.google.com/oauthplayground`.
3. Dans OAuth Playground, choisir « Use your own OAuth credentials », autoriser la portée `https://www.googleapis.com/auth/blogger`, puis obtenir un **refresh token**.
4. Dans GitHub **Settings → Secrets and variables → Actions**, ajouter les secrets :
   - `BLOGGER_CLIENT_ID`
   - `BLOGGER_CLIENT_SECRET`
   - `BLOGGER_REFRESH_TOKEN`
   - `BLOGGER_BLOG_ID` (facultatif, le script peut chercher le blog depuis son URL)
5. Relancer le workflow. Les chansons en attente pourront être publiées sur Blogger.

Attention : les jetons d'actualisation des applications OAuth en mode **Testing** peuvent expirer après 7 jours. Le compte Google autorisé doit être administrateur ou auteur du blog.

## Préférer des brouillons ?
Dans `.github/workflows/soundcloud-sync.yml`, modifier `BLOGGER_AS_DRAFT: 'false'` en `'true'`.

## Limites
- GitHub Pages est public.
- Les articles générés utilisent une introduction générique ; le système ne connaît pas automatiquement les histoires des chansons.
- La publication sur Blogger n'est **pas active** tant que les secrets OAuth ne sont pas renseignés.
- GitHub Actions ne fonctionne pas en temps réel ; les exécutions programmées peuvent être retardées.
- Un changement d'identifiant de piste côté SoundCloud pourrait créer un doublon.
