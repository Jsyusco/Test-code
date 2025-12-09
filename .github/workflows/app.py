# --- IMPORTS ET PRÉPARATION ---
import streamlit as st
import io
import json
import re
from datetime import datetime
import os

# Importation spécifique pour Google Drive
try:
    from pydrive2.auth import GoogleAuth
    from pydrive2.drive import GoogleDrive
    from google.oauth2 import service_account
    # from google.auth.transport.requests import AuthorizedSession # N'est plus utilisé directement
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

# --- FONCTION D'INITIALISATION GOOGLE DRIVE (CORRIGÉE et ROBUSTE) ---

@st.cache_resource(show_spinner="Initialisation de Google Drive...")
def init_google_drive():
    """Initialise l'objet Google Drive et le stocke dans st.session_state."""
    
    if not GOOGLE_DRIVE_AVAILABLE:
        st.session_state.drive_initialized = False
        return False
        
    if "google_drive" not in st.secrets:
        st.error("⚠️ Secret 'google_drive' non trouvé. Vérifiez `secrets.toml`.")
        st.session_state.drive_initialized = False
        return False

    try:
        # Reconstruire l'objet JSON du compte de service à partir des secrets individuels
        # (Cette méthode évite les erreurs de caractère de contrôle JSON)
        json_key_info = {
            "type": st.secrets["google_drive"]["type"],
            "project_id": st.secrets["google_drive"]["project_id"],
            "private_key_id": st.secrets["google_drive"]["private_key_id"],
            "private_key": st.secrets["google_drive"]["private_key"], # Clé échappée
            "client_email": st.secrets["google_drive"]["client_email"],
            "client_id": st.secrets["google_drive"]["client_id"],
            "auth_uri": st.secrets["google_drive"]["auth_uri"],
            "token_uri": st.secrets["google_drive"]["token_uri"],
            "auth_provider_x509_cert_url": st.secrets["google_drive"]["auth_provider_x509_cert_url"],
            "client_x509_cert_url": st.secrets["google_drive"]["client_x509_cert_url"],
            "universe_domain": st.secrets["google_drive"].get("universe_domain", "googleapis.com")
        }
        
        # 1. Création des identifiants Google OAuth
        creds = service_account.Credentials.from_service_account_info(
            json_key_info,
            scopes=['https://www.googleapis.com/auth/drive']
        )
        
        # 2. Utilisation de GoogleAuth pour la compatibilité avec pydrive2
        #    Ceci corrige l'erreur 'access_token_expired'
        gauth = GoogleAuth()
        gauth.credentials = creds 
        drive = GoogleDrive(gauth)
        
        # 3. Récupération de l'ID du dossier cible
        folder_id = st.secrets["google_drive"]["target_folder_id"] 
        
        # 4. Stockage des objets dans l'état de session
        st.session_state.drive_obj = drive
        st.session_state.folder_id = folder_id
        st.session_state.drive_initialized = True
        
        st.success("✅ Google Drive initialisé avec succès. Prêt à uploader.")
        return True

    except Exception as e:
        st.error(f"❌ ÉCHEC de l'initialisation de Google Drive : {e}")
        st.caption("Veuillez vérifier les valeurs individuelles de votre compte de service dans `secrets.toml`.")
        st.session_state.drive_initialized = False
        return False

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
            
            file_drive.content = io.BytesIO(uploaded_file.getvalue())
            
            # Uploader
            file_drive.Upload()
            
        st.success(f"🎉 Fichier uploadé avec succès sur Drive : **{file_name}**")
        st.info(f"Vérifiez le dossier Google Drive ID : `{folder_id}`")
        return True
    except Exception as e:
        st.error(f"❌ Échec de l'upload du fichier : {e}")
        st.warning("Vérifiez les permissions (rôle Éditeur) de votre clé de service pour l'écriture dans le dossier cible.")
        return False

# --- BOUCLE PRINCIPALE DE TEST ---

def main():
    st.markdown("<div class='main-header'><h1>Test de Connexion Google Drive</h1></div>", unsafe_allow_html=True)
    
    # 1. Tenter l'initialisation de Drive (Le résultat est stocké dans st.session_state)
    init_success = init_google_drive()
    
    if not init_success:
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
        if st.session_state.drive_initialized:
            st.info(f"Tentative d'upload du fichier : {uploaded_file.name}")
            # Les objets sont récupérés de st.session_state, ce qui élimine la NameError
            upload_file_to_drive(st.session_state.drive_obj, st.session_state.folder_id, uploaded_file) 
        else:
            st.error("L'objet Drive n'est pas initialisé. Veuillez rafraîchir ou vérifier la configuration.")
    elif submitted and uploaded_file is None:
        st.warning("Veuillez sélectionner un fichier avant d'uploader.")

if __name__ == '__main__':
    # Initialisation des clés de session avant tout appel à main()
    if 'drive_initialized' not in st.session_state:
        st.session_state.drive_initialized = False
    if 'drive_obj' not in st.session_state:
        st.session_state.drive_obj = None
    if 'folder_id' not in st.session_state:
        st.session_state.folder_id = None
        
    main()
