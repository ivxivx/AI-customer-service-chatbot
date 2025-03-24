import sqlite3
from langchain_community.agent_toolkits.sql.base import create_sql_agent
from langchain_community.agent_toolkits.sql.toolkit import SQLDatabaseToolkit
from langchain_community.utilities import SQLDatabase
from langchain.agents import AgentExecutor
from langchain.agents.agent_types import AgentType

CHAT_DB = 'chat.db'

prompt_format_instructions = """Use the following format:

Question: the input question you must answer
Thought: you should always think about what to do
Action: the action to take, should be one of [{tool_names}]
Action Input: the input to the action
Observation: the result of the action
... (this Thought/Action/Action Input/Observation can repeat N times)
Thought: I now know the final answer
Final Answer: the final answer to the original input question, which should include the following 4 parameters: 1. a mandatory flag named found, if no record is found or "no records" is returned by your SQL query, return found as false, otherwise return as true. 2. the record found. 3. the table name named table_name from which a record is found. 4. a mandatory explanation named justification which contains the reason and SQL query yo used to search for record. You must give Final Answer in valid JSON format without any extra content.

"""


def prepare_data():
    conn = sqlite3.connect(CHAT_DB)
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS payment (id TEXT PRIMARY KEY, amount REAL, created_at TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS payout (id TEXT PRIMARY KEY, amount REAL, created_at TEXT)')

    c.execute('INSERT INTO payment (id, amount, created_at) VALUES (?, ?, ?) ON CONFLICT DO NOTHING', ('payment-a1c1', 100.0, '2021-01-01 00:00:00'))
    c.execute('INSERT INTO payment (id, amount, created_at) VALUES (?, ?, ?) ON CONFLICT DO NOTHING', ('payment-b1c2', 200.0, '2021-01-02 00:00:00'))

    c.execute('INSERT INTO payout (id, amount, created_at) VALUES (?, ?, ?) ON CONFLICT DO NOTHING', ('payout-a2c1', 50.0, '2021-01-01 00:00:00'))
    c.execute('INSERT INTO payout (id, amount, created_at) VALUES (?, ?, ?) ON CONFLICT DO NOTHING', ('payout-b2c2', 100.0, '2021-01-02 00:00:00'))
    conn.commit()
    conn.close()

def create_sql_agent_executor(llm):
    db = SQLDatabase.from_uri(f"sqlite:///{CHAT_DB}")

    toolkit = SQLDatabaseToolkit(db=db, llm=llm)
    agent_executor = create_sql_agent(
        format_instructions=prompt_format_instructions,
        llm=llm,
        toolkit=toolkit,
        verbose=True,
        agent_type=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
        agent_executor_kwargs={'handle_parsing_errors':True},
        early_stopping_method='force',
        max_iterations=20,
    )
    
    return agent_executor

