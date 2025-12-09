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
    from google.oauth2 import service_account # Import utilisé dans l'initialisation
    from google.auth.transport.requests import AuthorizedSession # <--- Import de l'objet non compatible
    GOOGLE_DRIVE_AVAILABLE = True
except ImportError:
    # Ce message d'erreur s'affiche si les dépendances ne sont pas installées.
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

# --- FONCTION DE NETTOYAGE AMÉLIORÉE POUR LA ROBUSTESSE ---
def clean_json_string(json_string):
    """
    Nettoie la chaîne JSON pour supprimer les caractères de contrôle non valides.
    """
    if not isinstance(json_string, str):
        return json_string
        
    # Pattern : remplace tout ce qui n'est pas un caractère imprimable ASCII (\x20-\x7E)
    # ou un caractère de contrôle "sûr" (\t, \n, \r) par une chaîne vide.
    cleaned_string = re.sub(r'[^\x20-\x7E\t\n\r]', '', json_string)
    return cleaned_string

# --- FONCTION D'INITIALISATION GOOGLE DRIVE (INITIALE - CAUSE DU BUG) ---

@st.cache_resource(show_spinner="Initialisation de Google Drive...")
def init_google_drive():
    try:
        # Reconstruire l'objet JSON du compte de service à partir des secrets individuels
        json_key_info = {
            "type": st.secrets["google_drive"]["type"],
            "project_id": st.secrets["google_drive"]["project_id"],
            "private_key_id": st.secrets["google_drive"]["private_key_id"],
            "private_key": st.secrets["google_drive"]["private_key"], # Utilise la clé échappée
            "client_email": st.secrets["google_drive"]["client_email"],
            "client_id": st.secrets["google_drive"]["client_id"],
            "auth_uri": st.secrets["google_drive"]["auth_uri"],
            "token_uri": st.secrets["google_drive"]["token_uri"],
            "auth_provider_x509_cert_url": st.secrets["google_drive"]["auth_provider_x509_cert_url"],
            "client_x509_cert_url": st.secrets["google_drive"]["client_x509_cert_url"],
            "universe_domain": st.secrets["google_drive"].get("universe_domain", "googleapis.com")
        }

        # 1. Création des identifiants (Utilisation de google.oauth2.service_account)
        creds = service_account.Credentials.from_service_account_info(
            json_key_info,
            scopes=['https://www.googleapis.com/auth/drive']
        )
        
        # 2. Création de la session (Utilisation de AuthorizedSession non compatible avec pydrive2)
        http_auth = AuthorizedSession(creds)
        drive = GoogleDrive(http_auth) # <--- C'est ici que l'erreur se produit
        
        # 3. Récupération de l'ID du dossier cible
        folder_id = st.secrets["google_drive"]["target_folder_id"] # Clé requise
        
        st.success("✅ Google Drive initialisé avec succès. Prêt à uploader.")
        return drive, folder_id

    except Exception as e:
        st.error(f"❌ ÉCHEC de l'initialisation de Google Drive : {e}")
        st.caption("Veuillez vérifier les valeurs individuelles de votre compte de service dans `secrets.toml`.")
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
