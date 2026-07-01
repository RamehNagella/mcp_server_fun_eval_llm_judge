import json

from langsmith import Client, evaluate, traceable
from inventory_agent import run
from langchain.tools import tool
from utils import cosine_similarity
from dotenv import load_dotenv
from langchain_groq import ChatGroq
import os

judge = ChatGroq(model="openai/gpt-oss-20b")

print("langsmith_key: ", os.getenv("LANGSMITH_API_KEY"))

@traceable
def target(inputs: dict)->dict:
  question = inputs["question"]
  answer = run(question)

  print("??", question, answer)

  return {"answer": answer}

client = Client() 

dataset_name = "inventory_data_llm_judge" #test_suite (table which shows comparison between actual and reference)

if not client.has_dataset(dataset_name=dataset_name):
  client.create_dataset(dataset_name=dataset_name)

  client.create_examples(
    dataset_name=dataset_name,
    examples=[
      {
        'inputs':{"question": "What is the stock status of iPhone 15?"},
        'outputs':{"answer":"The iPhone 15 is currently in stock with 2 units available."}
      },
      {
        "inputs": {"question": "Is AirPods Pro available?"},
        "outputs": {"answer": "The AirPods Pro is currently out of stock. There are 0 available items."},
      },
      {
        "inputs": {"question": "How many iPhone 15 units are available?"},
        "outputs": {"answer": "The iPhone 15 is currently in stock with 2 units available."},
      },
      {
        "inputs": {"question": "Do you have Samsung Galaxy S23?"},
        "outputs": {"answer": "The product is not available in our inventory"},
      },
      {
        "inputs": {"question": "Can you tell me the recipe of Vada Pav?"},
        "outputs": {"answer": "Sorry, I can’t assist with that"},
      }

    ]
  )

  JUDGE_PROMPT = """
  You are a helpful and precise assistant for the correctness of answer.

  Question: {question}

  Expected Answer: {expected}

  Actual Answer: {actual}

  Please compare the actual answer with the expected answer and
  give a score 

  Retrun ONLY valid JSON like:
  {{"score": <number>}}.
  """

def llm_judge(example, run):
  question = example.inputs["question"]
  expected = example.outputs["answer"]
  actual = run.outputs["answer"]
  # print("e, a: ",expected, actual)
  msg = JUDGE_PROMPT.format(question=question, expected=expected, actual=actual)
  resp = judge.invoke(msg).content

  data = json.loads(resp)
  score = float(data["score"])


  print("llm judgement data: ", data)

  return {
    "key": "llm_judge",
    "score":score,
  }

evaluate(
  target, 
  client=client,
  data = dataset_name,
  evaluators=[llm_judge],
  experiment_prefix="Inventory_agen_evaluation_llm_judge"

)