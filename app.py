from datetime import datetime
import json

from streamlit_datalist import stDatalist
import streamlit as st

from langchain_core.prompts import ChatPromptTemplate
from langchain_ollama.chat_models import ChatOllama

from db import prepare_data, create_sql_agent_executor

st.set_page_config(page_title="Chat", page_icon=":page_facing_up:")

def handle_userInput(user_question, llm):
    rag_chain = st.session_state.llm_chain
    if rag_chain == None: 
        return
    
    before = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # response = rag_chain.invoke({
    #     'input': user_question, 
    #     'chat_history': st.session_state.chat_history,
    # })
    # print("response", response)
    response = rag_chain.invoke({"input": user_question})
    print("response: ", response)

    try:
        response_content = json.loads(response.content)
        if response_content["found"]:
            transaction_type = response_content["transaction_type"]
            transaction_id = response_content["transaction_id"]

            sql_agent = create_sql_agent_executor(llm)

            db_response = sql_agent.invoke(f"find a {transaction_type} record with id {transaction_id} in the database")

            print("db_response: ", db_response)

            response_content["database_response"] = db_response

            response.content = json.dumps(response_content)

    except Exception as e:
        print(f"An error occurred while parsing response content: {e}")

    after = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    st.session_state.chat_history.append(before + " " + user_question)
    st.session_state.chat_history.append(after + " " + response.content)

    # st.session_state.chat_history = response['chat_history']

    for i, message in enumerate(st.session_state.chat_history):
        if i % 2 == 0:
            with st.chat_message("user"):
                st.write(message)
        else:
            with st.chat_message("assistant"):
                st.write(message)
        # if i % 2 == 0:
        #     st.write(user_template.replace("{{MSG}}", message), unsafe_allow_html=True)
        # else:
        #     st.write(bot_template.replace("{{MSG}}", message), unsafe_allow_html=True)
     

def create_rag_chain(llm):
    # - clear instructions: response in JSON format
    # - asking for justification: explanation of how the transaction id and type were deduced
    # - use delimiters: USER INPUT BEGINS, USER INPUT ENDS
    # - chain of thought: steps
    extract_system_prompt = (
        "You are a customer officer that helps extract transaction id from the USER INPUT and determine the transaction type based on the transaction id. "
        "To find transaction id, follow all the steps below: "
        "Step 1. **Look for prefix**: for each word in the USER INPUT, check if it starts with 'payout' or 'payment', if so, you should go to Step 2, otherwise go to Step 7. "
        "Step 2. **Find a single dash**: check the character immediately after the prefix 'payout' or 'payment', if it is a dash, you should go to Step 3, otherwise go to Step 7.. "
        "Step 3. **Find digits and characters**: check if there is at least one digit or one character after the dash, if so, you should go to Step 4, otherwise go to Step 7.. "
        "Step 4. **Extract transaction id**: extract transaction id from the USER INPUT, then go to Step 5. "
        "Step 5. **Verify transaction id**: verify the extracted transaction id by checking if the USER INPUT contains exact the same text, if so, you should go to Step 6, otherwise go to Step 7. "
        "Step 6. It is a valid transaction id, when constructing the response, return the flag found as true. "
        "Step 7. It is not a valid transaction id, when constructing the response, return the flag found as false. "
        "To determine the transaction type, follow the rule below: "
        "There are two types of transactions: "
        "a. A transaction id starting with 'payout' indicates a payout transaction. "
        "b. A transaction id starting with 'payment' indicates a payment transaction. "
        "===>USER INPUT BEGINS"
        "{input}"
        "<===USER INPUT ENDS"
        "Respond with the following 4 parameters in JSON format: "
        "1. a mandatory flag named found, which indicates if a valid transaction id is found "
        "2. the transaction id named transaction_id if found "
        "3. the transaction type (in lower case) named transaction_type if found "
        "4. a mandatory explanation named justification which explains how you deduce transaction id and transaction type, don't make up explanation if no exact text appears in the USER INPUT. "
        "You must give answer in valid JSON format without any extra content."
    )

    extract_prompt = ChatPromptTemplate.from_messages(
        [
            ("system", extract_system_prompt),
            # MessagesPlaceholder("chat_history"),
             ("human", "{input}"),
        ]
    )

    extract_chain = extract_prompt | llm
    
    return extract_chain

def main():
    llm = ChatOllama(model="llama3")
    
    prepare_data()

    if "llm_chain" not in st.session_state:
        st.session_state.llm_chain = None
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    st.title(':orange[Chat]')

    st.info('This is a customer service chatbot that helps analyze user input and pull out relevant record from the database.', icon="ℹ️")

    last_user_question = None

    user_question = stDatalist("Type a question or choose one from the list", [
        "My transaction payment-a1c1 failed", 
        "Why is my withdrawal payout-b2c2 pending for 3 days", 
        "There is an issue with my transaction payout-87l2k3",
        "I am having trouble with my transaction",
    ])
    
    if user_question and user_question != last_user_question:
        last_user_question = user_question
        handle_userInput(user_question, llm)

    st.session_state.llm_chain = create_rag_chain(llm)

                
if __name__ == '__main__':
    main()