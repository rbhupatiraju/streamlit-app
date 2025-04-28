import streamlit as st
import PyPDF2
from io import BytesIO
import base64
import fitz  # PyMuPDF

st.set_page_config(layout="wide")

st.markdown("""
    <style>
        .reportview-container {
            margin-top: -2em;
        }
        #MainMenu {visibility: hidden;}
        .stDeployButton {display:none;}
        footer {visibility: hidden;}
        #stDecoration {display:none;}
    </style>
""", unsafe_allow_html=True)

def display_page_with_highlights(uploaded_file, page_number):
    # Create a PDF document object
    doc = fitz.open(stream=uploaded_file.getvalue(), filetype="pdf")
    
    # Get the selected page
    page = doc[page_number]
    
    # Convert page to PNG image with higher resolution for better quality
    pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))  # 2x zoom for better resolution
    
    # Convert to bytes
    img_bytes = pix.tobytes()
    
    # Convert to base64
    base64_img = base64.b64encode(img_bytes).decode()
    
    # Create HTML for displaying the image
    img_display = f'<img src="data:image/png;base64,{base64_img}" style="width: 100%; height: auto;">'
    
    doc.close()

    return img_display

def main():
    st.title("PDF Evaluator")

    # Initialize session state for page number if it doesn't exist
    if 'page_number' not in st.session_state:
        st.session_state.page_number = 0
    
    # File uploader
    uploaded_file = st.file_uploader("Choose a PDF file", type="pdf")

    if 'uploaded_file' in st.session_state and uploaded_file is not None and st.session_state.uploaded_file != uploaded_file.name:
        st.session_state.page_number = 0

    if uploaded_file is not None:
        st.session_state.uploaded_file = uploaded_file.name
    
    if uploaded_file is not None:

        # Read PDF file
        pdf_bytes = BytesIO(uploaded_file.read())
        pdf_reader = PyPDF2.PdfReader(pdf_bytes)
        total_pages = len(pdf_reader.pages)
        
        # Create two columns
        col1, col2 = st.columns(2)
        
        with col1:

            current_page = st.session_state.page_number
            
            # Display current page with highlights
            page_display = display_page_with_highlights(uploaded_file, current_page)
            st.markdown(page_display, unsafe_allow_html=True)
            
            # Add some spacing
            st.write("")
            
            # Navigation controls at the bottom with custom styling
            nav_col1, nav_col2, nav_col3 = st.columns([1, 3, 1])
            
            # Custom CSS for the buttons and page number
            st.markdown("""
                <style>
                    .stButton>button {
                        padding: 0.2rem 1rem;
                        min-height: 0px;
                        height: 30px;
                    }
                    div[data-testid="column"] {
                        text-align: center;
                    }
                    .page-number {
                        font-size: 0.8rem;
                        margin-top: 8px;
                        color: #666;
                    }
                </style>
            """, unsafe_allow_html=True)
            
            with nav_col1:
                if st.button("←", key="prev_button", disabled=st.session_state.page_number <= 0):
                    st.session_state.page_number -= 1
                    st.rerun()
            with nav_col2:
                st.markdown(f"<p class='page-number'>Page {st.session_state.page_number + 1} of {total_pages}</p>", unsafe_allow_html=True)
            
            with nav_col3:
                if st.button("→", key="next_button", disabled=st.session_state.page_number >= total_pages - 1):
                    st.session_state.page_number += 1
                    st.rerun()
        
        with col2:
            
            # Create two tabs
            tab1, tab2 = st.tabs(["Checks", "Chat"])
            
            with tab1:

                # Create nested tabs for different check categories
                check_tab1, check_tab2, check_tab3, check_tab4 = st.tabs(["Document Structure", "Content Quality", "Visual Elements", "Formatting"])

                # Add accordion sections with checklists
                with check_tab1:
                    st.checkbox("Title page present")
                    st.checkbox("Table of contents included") 
                    st.checkbox("Page numbers consistent")
                    st.checkbox("Headers and footers consistent")

                with check_tab2:
                    st.checkbox("No spelling errors")
                    st.checkbox("Grammar is correct")
                    st.checkbox("Citations properly formatted")
                    st.checkbox("References complete")

                with check_tab3:
                    st.checkbox("Images are clear")
                    st.checkbox("Tables properly formatted")
                    st.checkbox("Figures numbered correctly")
                    st.checkbox("Captions present")

                with check_tab4:
                    st.checkbox("Font consistent")
                    st.checkbox("Margins correct")
                    st.checkbox("Line spacing uniform")
                    st.checkbox("Paragraph alignment consistent")
            
            with tab2:
                
                # Initialize chat history in session state if it doesn't exist
                if "messages" not in st.session_state:
                    st.session_state.messages = []
                
                # Display chat messages
                for message in st.session_state.messages:
                    with st.chat_message(message["role"]):
                        st.markdown(message["content"])
                
                # Chat input
                if prompt := st.chat_input("Ask a question about the document"):
                    # Add user message to chat history
                    st.session_state.messages.append({"role": "user", "content": prompt})
                    
                    # Display user message
                    with st.chat_message("user"):
                        st.markdown(prompt)
                    
                    # Display assistant response
                    with st.chat_message("assistant"):
                        response = "I'm analyzing the document to answer your question..."
                        st.markdown(response)
                        st.session_state.messages.append({"role": "assistant", "content": response})

if __name__ == "__main__":
    main() 