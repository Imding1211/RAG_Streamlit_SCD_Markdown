
from database_controller import DatabaseController
from setting_controller import SettingController
from query_controller import QueryController

import streamlit as st
import uuid

#=============================================================================#

DatabaseController = DatabaseController()
QueryController    = QueryController()

#=============================================================================#

def load_PDF(PDF_name):
    with open(f"save_PDF/{PDF_name}", "rb") as PDF_file:
        PDF = PDF_file.read()

    return PDF

#=============================================================================#

st.set_page_config(layout="wide")

if "messages" not in st.session_state or "memory" not in st.session_state:
    st.session_state.messages = [{"role": "system", "content": "使用繁體中文回答問題", "source": []}]
    st.session_state.memory   = [{"role": "system", "content": "使用繁體中文回答問題", "source": []}]

    if len(DatabaseController.calculate_existing_ids()) == 0:
        info = "👈 Hi~ 資料庫是空的，請先到Database頁面點選上傳資料。"
    else:
        info = "✋ Hi~ 請問想詢問什麼問題呢？"
    
    st.session_state.messages.append({"role": "assistant", "content": info, "source": []})
    st.session_state.memory.append({"role": "assistant", "content": info, "source": []})

#=============================================================================#

st.title("資料查詢")

col1, col2 = st.columns(2)

chat_container = col1.container(border=False, height=500)
text_container = col2.container(border=False, height=500)

#-----------------------------------------------------------------------------#

for message in st.session_state.messages[1:]:

    if message["role"] == "user":
        with chat_container.chat_message("user", avatar="🦖"):
            st.markdown(message["content"])

    else:
        with chat_container.chat_message("assistant", avatar="🤖"):
            st.markdown(message["content"])

            if len(message["source"]):
                st.caption("資料來源: " + ", ".join(message["source"]))

                st.divider()

                st.caption("資料下載:")
                download_buttons = []
                for index, source in enumerate(message["source"]):
                    download_buttons.append(st.download_button(key=uuid.uuid4(), label=source, data=load_PDF(source), file_name=source, mime='application/octet-stream'))

#-----------------------------------------------------------------------------#

if question := st.chat_input("輸入問題"):

    with chat_container.chat_message("user", avatar="🦖"):
        st.markdown(question)

#-----------------------------------------------------------------------------#

    results, sources = QueryController.generate_results(question)

    prompt, raw_text = QueryController.generate_prompt(question, results)

    st.session_state.messages.append({"role": "user", "content": question, "source": []})
    st.session_state.memory.append({"role": "user", "content": prompt, "source": []})

#-----------------------------------------------------------------------------#

    with chat_container.chat_message("assistant", avatar="🤖"):
        response = st.write_stream(QueryController.generate_response(st.session_state.memory))

        if len(sources):
            st.caption("參考資料來源: " + ", ".join(sources))

            st.divider()

            st.caption("參考資料下載:")
            download_buttons = []
            for index, source in enumerate(sources):
                download_buttons.append(st.download_button(key=uuid.uuid4(), label=source, data=load_PDF(source), file_name=source, mime='application/octet-stream'))

    st.session_state.memory[-1]["content"] = question

    st.session_state.messages.append({"role": "assistant", "content": response, "source": sources})
    st.session_state.memory.append({"role": "assistant", "content": response, "source": sources})

    text_container.markdown(raw_text, unsafe_allow_html=True)

