# --- IMPORTS ET PRÉPARATION ---
import streamlit as st
import io
import json
import re
from datetime import datetime
import os

# Importation spécifique pour Google Drive
try:
    # Nécessaire pour pydrive2
    from pydrive2.auth import GoogleAuth
    from pydrive2.drive import GoogleDrive
    from google.oauth2 import service_account
    from google.auth.transport.requests import AuthorizedSession
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
</style>
""", unsafe_allow_html=True)

# --- FONCTION DE NETTOYAGE POUR LA ROBUSTESSE ---
def clean_json_string(json_string):
    """
    Nettoie la chaîne JSON pour supprimer les caractères de contrôle non valides 
    qui peuvent causer l'erreur 'Invalid control character' lors du json.loads().
    """
    if not isinstance(json_string, str):
        return json_string
    # Supprime les caractères de contrôle non imprimables qui cassent l'analyse JSON.
    cleaned_string = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', json_string)
    return cleaned_string

# --- FONCTION D'INITIALISATION GOOGLE DRIVE ---

@st.cache_resource(show_spinner="Initialisation de Google Drive...")
def init_google_drive():
    """Initialise l'objet Google Drive à partir des secrets Streamlit."""
    
    if "google_drive" not in st.secrets:
        st.error("⚠️ Secret 'google_drive' non trouvé dans secrets.toml. Veuillez configurer la clé de service et l'ID du dossier cible.")
        return None, None

    try:
        json_key_info_str = st.secrets["google_drive"]["service_account_json"]
        
        # Nettoyage de la chaîne JSON
        cleaned_json_key_info_str = clean_json_string(json_key_info_str)
        
        # Chargement du JSON
        json_key_info = json.loads(cleaned_json_key_info_str) 
        
        # Vérification optionnelle de la clé
        if len(json_key_info.get("private_key", "")) < 500: 
            st.warning("⚠️ La clé privée semble courte. Cela peut indiquer un problème de secret non formaté correctement.")
        
        # Création des identifiants
        creds = service_account.Credentials.from_service_account_info(
            json_key_info,
            scopes=['https://www.googleapis.com/auth/drive']
        )
        
        http_auth = AuthorizedSession(creds)
        drive = GoogleDrive(http_auth)
        
        folder_id = st.secrets["google_drive"].get("target_folder_id")
        
        if not folder_id:
            st.error("❌ 'target_folder_id' est manquant dans la section [google_drive] du secret.")
            return None, None
            
        st.success("✅ Google Drive initialisé avec succès. Prêt à uploader.")
        return drive, folder_id

    except Exception as e:
        st.error(f"❌ ÉCHEC de l'initialisation de Google Drive : {e}")
        st.caption("Veuillez vérifier le formatage de votre clé de service JSON dans `secrets.toml`.")
        return None, None

# --- FONCTION DE SAUVEGARDE DE FICHIER UNIQUE ---

def upload_file_to_drive(drive, folder_id, uploaded_file):
    """Sauvegarde un unique objet UploadedFile dans Google Drive."""
    
    if not drive or not folder_id:
        st.error("Google Drive non initialisé. Upload impossible.")
        return False

    file_name = f"TEST_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uploaded_file.name}"
    
    try:
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
        st.warning("Vérifiez les permissions de votre clé de service pour l'écriture dans le dossier cible.")
        return False

# --- BOUCLE PRINCIPALE DE TEST ---

def main():
    st.markdown("<div class='main-header'><h1>Test de Connexion Google Drive</h1></div>", unsafe_allow_html=True)
    
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
            type=["png", "jpg", "jpeg", "pdf", "txt"]
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
