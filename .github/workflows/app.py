# --- IMPORTS ET PRÉPARATION ---
import streamlit as st
import io
import re
from datetime import datetime
import os # Import maintenu mais non utilisé directement ici

# Importation spécifique pour Google Drive
try:
    # Nécessaire pour pydrive2
    from pydrive2.auth import GoogleAuth
    from pydrive2.drive import GoogleDrive
    # ATTENTION : Les imports ci-dessous ne sont plus nécessaires 
    # pour le flux d'authentification pydrive2 natif et ont été retirés/omis.
    # from google.oauth2 import service_account 
    # from google.auth.transport.requests import AuthorizedSession 
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

# --- FONCTION DE NETTOYAGE (Gardée par précaution, mais potentiellement inutile si la clé est bien formatée dans secrets.toml) ---
def clean_json_string(json_string):
    """Nettoie la chaîne JSON pour la private_key."""
    if not isinstance(json_string, str):
        return json_string
        
    # Pattern : remplace tout ce qui n'est pas un caractère imprimable ASCII (\x20-\x7E)
    # ou un caractère de contrôle "sûr" (\t, \n, \r) par une chaîne vide.
    cleaned_string = re.sub(r'[^\x20-\x7E\t\n\r]', '', json_string)
    return cleaned_string

# --- FONCTION D'INITIALISATION GOOGLE DRIVE (CORRIGÉE) ---

@st.cache_resource(show_spinner="Initialisation de Google Drive...")
def init_google_drive():
    """Initialise l'objet GoogleDrive en utilisant l'authentification par compte de service pydrive2."""
    if not GOOGLE_DRIVE_AVAILABLE:
        return None, None
        
    try:
        # 1. Initialisation de GoogleAuth
        gauth = GoogleAuth()

        # 2. Définir les paramètres d'authentification pour utiliser le compte de service
        gauth.settings['service_account'] = True
        gauth.settings['oauth_scope'] = ['https://www.googleapis.com/auth/drive'] # Scope nécessaire pour l'upload

        # 3. Récupérer les identifiants du compte de service depuis Streamlit Secrets
        client_email = st.secrets["google_drive"]["client_email"]
        # La clé privée DOIT inclure les retours à la ligne (\n)
        private_key = st.secrets["google_drive"]["private_key"]
        
        # 4. Charger les identifiants
        # Cette méthode est native à pydrive2 et compatible avec GoogleDrive()
        gauth.LoadServiceAccountCredentials(client_email, private_key)
        
        # 5. Créer l'objet GoogleDrive avec l'objet d'authentification configuré
        drive = GoogleDrive(gauth)
        
        # 6. Récupération de l'ID du dossier cible
        folder_id = st.secrets["google_drive"]["target_folder_id"] 
        
        st.success("✅ Google Drive initialisé avec succès. Prêt à uploader.")
        return drive, folder_id

    except Exception as e:
        st.error(f"❌ ÉCHEC de l'initialisation de Google Drive : {e}")
        st.caption("Veuillez vérifier les valeurs individuelles de votre compte de service dans `secrets.toml`, en particulier la `private_key`.")
        return None, None

# --- FONCTION DE SAUVEGARDE DE FICHIER UNIQUE ---

def upload_file_to_drive(drive, folder_id, uploaded_file):
    """Sauvegarde un unique objet UploadedFile dans Google Drive."""
    
    if not drive or not folder_id:
        st.error("Google Drive non initialisé. Upload impossible.")
        return False

    file_name = f"TEST_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uploaded_file.name}"
    
    try:
        with st.spinner(f"Upload en cours de {file_name}..."):
            # Créer le fichier sur Drive
            file_drive = drive.CreateFile({
                'title': file_name, 
                'parents': [{'id': folder_id}], 
                'mimeType': uploaded_file.type
            })
            
            # Lire les octets du fichier uploadé et les attribuer au contenu du fichier Drive
            file_drive.content = io.BytesIO(uploaded_file.getvalue())
            
            # Uploader
            file_drive.Upload()
            
        st.success(f"🎉 Fichier uploadé avec succès sur Drive : **{file_name}**")
        st.info(f"Vérifiez le dossier Google Drive ID : `{folder_id}`")
        return True
    except Exception as e:
        st.error(f"❌ Échec de l'upload du fichier : {e}")
        st.warning("Vérifiez les permissions de votre clé de service (rôle ÉDITEUR) pour l'écriture dans le dossier cible.")
        return False

# --- BOUCLE PRINCIPALE DE TEST ---

def main():
    st.markdown("<div class='main-header'><h1>Test de Connexion Google Drive</h1></div>", unsafe_allow_html=True)
    
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
    
    # 2. Formulaire d'Upload
    with st.form(key='drive_upload_form', clear_on_submit=True):
        st.markdown("<div class='phase-block'>", unsafe_allow_html=True)
        st.markdown("<h2>Upload de Fichier Test</h2>", unsafe_allow_html=True)
        
        uploaded_file = st.file_uploader(
            "Sélectionnez un fichier (Image, PDF, etc.) à uploader sur Drive", 
            key="test_file_uploader", 
            type=["png", "jpg", "jpeg", "pdf", "txt", "csv"]
        )
        
        submitted = st.form_submit_button("📤 Uploader sur Google Drive")
        st.markdown("</div>", unsafe_allow_html=True)

    # 3. Traitement de la Soumission
    if submitted and uploaded_file is not None:
        st.info(f"Tentative d'upload du fichier : {uploaded_file.name}")
        upload_file_to_drive(drive, folder_id, uploaded_file)
    elif submitted and uploaded_file is None:
        st.warning("Veuillez sélectionner un fichier avant d'uploader.")

if __name__ == '__main__':
    main()
