# --- IMPORTS ET PRÉPARATION ---
import streamlit as st
import io # Gardé au cas où l'utilisateur voudrait uploader plus tard
import re # Gardé par défaut, mais non utilisé dans cette version
from datetime import datetime
# Importation spécifique pour Google Drive
try:
    # Nécessaire pour pydrive2
    from pydrive2.auth import GoogleAuth
    from pydrive2.drive import GoogleDrive
    # Les imports de google.oauth2 et AuthorizedSession sont retirés car non compatibles avec pydrive2
    GOOGLE_DRIVE_AVAILABLE = True
except ImportError:
    st.error("🚨 Erreur: Le module 'pydrive2' ou ses dépendances sont manquants. Exécutez 'pip install pydrive2 google-api-python-client'.")
    GOOGLE_DRIVE_AVAILABLE = False
    
# --- CONFIGURATION ET STYLE ---
st.set_page_config(page_title="Test Google Drive", layout="centered")

st.markdown("""
<style>
    .stApp { background-color: #121212; color: #e0e0e0; }
    .main-header { background-color: #1e1e1e; padding: 20px; border-radius: 10px; margin-bottom: 20px; text-align: center; border-bottom: 3px solid #63B3ED; }
    .phase-block { background-color: #1e1e1e; padding: 25px; border-radius: 12px; margin-bottom: 20px; border: 1px solid #333; }
    .stSuccess, .stError, .stWarning { border-radius: 8px; padding: 10px; }
</style>
""", unsafe_allow_html=True)

# La fonction clean_json_string est retirée car non nécessaire avec l'authentification corrigée.

# --- FONCTION D'INITIALISATION GOOGLE DRIVE (CORRIGÉE) ---

@st.cache_resource(show_spinner="Initialisation de Google Drive...")
def init_google_drive():
    """Initialise l'objet GoogleDrive en utilisant l'authentification par compte de service pydrive2."""
    if not GOOGLE_DRIVE_AVAILABLE:
        return None, None
        
    try:
        # 1. Initialisation de GoogleAuth
        gauth = GoogleAuth()

        # 2. Récupérer les identifiants du compte de service depuis Streamlit Secrets
        client_email = st.secrets["google_drive"]["client_email"]
        private_key = st.secrets["google_drive"]["private_key"]
        
        # 3. Définir les paramètres d'authentification pour utiliser le compte de service
        gauth.settings['service_account'] = True
        # Utiliser le scope Drive complet pour la lecture (drive.readonly suffirait)
        gauth.settings['oauth_scope'] = ['https://www.googleapis.com/auth/drive'] 
        
        # 🚨 FIX du bug 'Missing required setting service_config' 
        # Configure manuellement les secrets pour pydrive2
        gauth.settings['client_config'] = {
            'client_email': client_email,
            'private_key': private_key
        }
        
        # 4. Charger les identifiants
        gauth.LoadServiceAccountCredentials(client_email, private_key)
        
        # 5. Créer l'objet GoogleDrive avec l'objet d'authentification configuré
        drive = GoogleDrive(gauth)
        
        # 6. Récupération de l'ID du dossier cible
        folder_id = st.secrets["google_drive"]["target_folder_id"] 
        
        st.success("✅ Google Drive initialisé avec succès. Prêt à lister les fichiers.")
        return drive, folder_id

    except Exception as e:
        st.error(f"❌ ÉCHEC de l'initialisation de Google Drive : {e}")
        st.caption("Veuillez vérifier les valeurs individuelles de votre compte de service dans `secrets.toml`.")
        return None, None

# --- NOUVELLE FONCTION DE LISTE DE FICHIERS ---

def list_files_in_drive_folder(drive, folder_id):
    """Liste les fichiers présents dans le dossier cible et les affiche dans Streamlit."""
    
    if not drive or not folder_id:
        st.error("Google Drive non initialisé. Liste impossible.")
        return

    st.markdown("<div class='phase-block'>", unsafe_allow_html=True)
    st.markdown(f"<h2>Contenu du dossier Drive</h2>", unsafe_allow_html=True)
    st.info(f"Dossier cible (ID) : `{folder_id}`")
    
    # Requête de recherche pydrive2 pour lister uniquement les fichiers (non-dossiers) dans le dossier cible
    # 'trashed = false' exclut les fichiers dans la corbeille.
    # 'mimeType != "application/vnd.google-apps.folder"' exclut les sous-dossiers.
    query = f"'{folder_id}' in parents and trashed = false and mimeType != 'application/vnd.google-apps.folder'"
    
    try:
        with st.spinner("Récupération de la liste des fichiers..."):
            # Obtient la liste des fichiers correspondant à la requête
            file_list = drive.ListFile({'q': query}).GetList()
            
        if not file_list:
            st.warning("Le dossier ne contient aucun fichier (ou aucun fichier non-dossier).")
            st.markdown("</div>", unsafe_allow_html=True)
            return

        st.success(f"🎉 **{len(file_list)}** fichiers trouvés dans le dossier.")
        
        # Préparer les données pour l'affichage
        data = []
        for file in file_list:
            # Conversion de la taille en Mo pour une meilleure lisibilité
            size_mb = f"{int(file.get('fileSize', 0)) / (1024*1024):.2f} Mo" if file.get('fileSize') else 'N/A'
            
            # Formater la date de modification
            modified_date = datetime.strptime(file['modifiedDate'], '%Y-%m-%dT%H:%M:%S.%fZ').strftime('%Y-%m-%d %H:%M:%S')

            data.append({
                "Nom du Fichier": file['title'],
                "Taille": size_mb,
                "Type MIME": file['mimeType'],
                "ID du Fichier": file['id'],
                "Modifié le": modified_date
            })

        # Afficher la liste des fichiers dans un tableau Streamlit
        st.dataframe(data, use_container_width=True)
        
    except Exception as e:
        st.error(f"❌ Échec de la récupération de la liste des fichiers : {e}")
        st.warning("Vérifiez que le compte de service a les permissions de LECTURE sur le dossier cible.")
        
    st.markdown("</div>", unsafe_allow_html=True)

# --- BOUCLE PRINCIPALE DE TEST ---

def main():
    st.markdown("<div class='main-header'><h1>Test de Connexion Google Drive et Liste des Fichiers</h1></div>", unsafe_allow_html=True)
    
    # Si les dépendances sont manquantes, on arrête l'exécution de la logique principale
    if not GOOGLE_DRIVE_AVAILABLE:
        st.markdown("---")
        st.error("Application arrêtée: Les modules requis sont manquants.")
        return

    # 1. Tenter l'initialisation de Drive
    drive, folder_id = init_google_drive()
    
    if not drive:
        st.markdown("---")
        st.warning("Arrêt du test : L'initialisation a échoué. Veuillez corriger le secret.")
        return

    st.markdown("---")
    
    # 2. Bouton pour déclencher la liste
    # La liste est affichée uniquement après que l'utilisateur clique sur le bouton
    st.markdown("<div class='phase-block'>", unsafe_allow_html=True)
    st.markdown("<h2>Action</h2>", unsafe_allow_html=True)
    
    if st.button("🔄 Actualiser et Afficher la Liste des Fichiers dans Drive", type="primary"):
        list_files_in_drive_folder(drive, folder_id)
        
    st.markdown("</div>", unsafe_allow_html=True)

if __name__ == '__main__':
    main()
