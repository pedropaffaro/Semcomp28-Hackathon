import pandas as pd
from faker import Faker
import random

# Inicializa o gerador de dados falsos
fake = Faker('pt_BR')

# Definições fixas
n = 10000
categorias = ["alimentação", "transporte", "despesas pessoais", "educação",
              "casa", "saúde", "lazer", "comunicação", "outros"]
formas_pagamento = ["pix", "cartão débito", "cartão crédito", "boleto"]

# Gera os dados
data = {
    "id_transacao": range(1, n + 1),
    "data": [fake.date_between(start_date='-20y', end_date='today') for _ in range(n)],
    "hora": [fake.time(pattern="%H:%M:%S") for _ in range(n)],
    "destinatario": [fake.company() for _ in range(n)],
    "valor": [round(random.uniform(5, 5000), 2) for _ in range(n)],
    "categoria": [random.choice(categorias) for _ in range(n)],
    "forma_pagamento": [random.choice(formas_pagamento) for _ in range(n)]
}

# Cria o DataFrame
df = pd.DataFrame(data)

# Salva em CSV
df.to_csv("transacoes_bancarias.csv", index=False, encoding="utf-8")

print("✅ Dataset 'transacoes_bancarias.csv' gerado com sucesso!")
print(df.head())
