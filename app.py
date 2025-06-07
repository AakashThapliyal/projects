import streamlit as st
import requests
import io
import contextlib
import google.generativeai as genai
import toml  # <-- Add this import

# App title
st.title("🖼️ OCR Image App with Gemini Code Correction")

# File uploader
uploaded_file = st.file_uploader("Choose an image...", type=["jpg", "jpeg", "png"])

# Initialize session state
if "enhanced_text" not in st.session_state:
    st.session_state.enhanced_text = ""

# Load secrets from secret.toml
secrets = toml.load("secret.toml")
GEMINI_API_KEY = secrets.get("api_key", "")
OCR_API_KEY = secrets.get("apikey", "")

if uploaded_file is not None:
    st.image(uploaded_file, caption="Uploaded Image", use_container_width=True)

    # Extract text from image (OCR)
    with st.spinner("🔍 Extracting text from image..."):
        file_bytes = uploaded_file.read()
        files = {
            "file": (uploaded_file.name, file_bytes, uploaded_file.type)
        }
        data = {"apikey": OCR_API_KEY}  # Use key from secret.toml

    try:
        response = requests.post("https://api.ocr.space/parse/image", files=files, data=data)
        response.raise_for_status()
        try:
            result = response.json()
        except Exception:
            st.error("OCR API returned a non-JSON response:")
            st.text(response.text)
            st.stop()

        parsed_text = ""

        if not result.get("IsErroredOnProcessing", True):
            parsed_results = result.get("ParsedResults")
            if parsed_results and isinstance(parsed_results, list) and len(parsed_results) > 0:
                parsed_text = parsed_results[0].get("ParsedText", "")
            else:
                parsed_text = "No text found in image."
        else:
            error_message = result.get("ErrorMessage", ["Unknown error"])
            if isinstance(error_message, list):
                parsed_text = "Error: " + error_message[0]
            else:
                parsed_text = "Error: " + str(error_message)

    except Exception as e:
        st.error(f"Failed to contact OCR API: {e}")
        st.stop()
        # Removed 'return' as it is not allowed outside a function

    # Show OCR text
    st.subheader("📝 OCR Extracted Text")
    st.text_area("Extracted Text", parsed_text, height=150)

    # Gemini Code Correction
    enhanced_text = ""
    if parsed_text and not parsed_text.startswith("Error:") and parsed_text.strip():
        if st.button("Enhance Code with Gemini"):
            with st.spinner("✨ Fixing code with Gemini..."):
                try:
                    # Gemini API key (now loaded from secret.toml)
                    genai.configure(api_key=GEMINI_API_KEY)

                    model = genai.GenerativeModel("gemini-2.0-flash")
                    chat = model.start_chat()

                    prompt = f"""Only return the corrected Python code below (no explanation, no notes, no extra text):

{parsed_text}
"""
                    gemini_response = chat.send_message(prompt)
                    enhanced_text = gemini_response.text.strip()

                    # Clean markdown from response
                    if enhanced_text.startswith("```"):
                        parts = enhanced_text.split("```")
                        if len(parts) >= 2:
                            enhanced_text = parts[1].replace("python", "", 1).strip()
                        else:
                            enhanced_text = parts[0].replace("python", "", 1).strip()

                except Exception as e:
                    enhanced_text = f"Error: {e}"
                st.session_state.enhanced_text = enhanced_text

    # Display Corrected Code
    enhanced_text = st.session_state.get("enhanced_text", "")
    if enhanced_text:
        st.subheader("🚀 Corrected Code")
        st.text_area("Corrected Python Code", enhanced_text, height=200)

        if not enhanced_text.startswith("Error:"):
            st.subheader("⚡ Run Corrected Code")
            st.code(enhanced_text, language="python")
            run_button = st.button("Execute Code")
            output_placeholder = st.empty()
            if run_button:
                code_output = io.StringIO()
                try:
                    with contextlib.redirect_stdout(code_output):
                        exec(enhanced_text, globals())  # use globals for proper execution
                    output_placeholder.text_area("Execution Output", code_output.getvalue(), height=200)
                except Exception as exec_err:
                    output_placeholder.text_area("Execution Output", f"Error during execution:\n{exec_err}", height=200)
